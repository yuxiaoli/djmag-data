import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import URLError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import sync
import enrich_profiles as enrich


class RankingRefreshTests(unittest.TestCase):
    def refresh(self, old, year=2026, rank=1):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            output = root / 'djs'
            output.mkdir()
            (output / 'david-guetta.json').write_text(json.dumps(old))
            fixture = root / 'ranking.html'
            fixture.write_text(''.join(
                f'<a href="/top100djs/{year}/{position}/{"david-guetta" if position == rank else "artist-" + str(position)}">Artist {position}</a>'
                for position in range(1, 101)))
            with patch.object(sys, 'argv', ['sync', '--fixture', str(fixture), '--output', str(output)]), contextlib.redirect_stdout(io.StringIO()):
                sync.main()
            return json.loads((output / 'david-guetta.json').read_text())

    def test_refresh_preserves_profile_provenance_and_historical_rankings(self):
        old = json.loads((ROOT / 'data/djs/david-guetta.json').read_text())
        old['rankings'].insert(0, dict(year=2025, rank=2, previous_rank=None,
            source_url='https://djmag.com/top100djs/2025/2/david-guetta'))
        old['sources'].append(dict(url=old['rankings'][0]['source_url'],
            publisher='DJ Mag', retrieved_at='2025-11-15T00:00:00Z', fields=['/rankings']))
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            output = root / 'djs'
            output.mkdir()
            (output / 'david-guetta.json').write_text(json.dumps(old))
            fixture = root / 'ranking.html'
            fixture.write_text(''.join(
                f'<a href="/top100djs/2026/{rank}/{"david-guetta" if rank == 1 else "artist-" + str(rank)}">Artist {rank}</a>'
                for rank in range(1, 101)))
            with patch.object(sys, 'argv', ['sync', '--fixture', str(fixture), '--output', str(output)]), contextlib.redirect_stdout(io.StringIO()):
                sync.main()
            current = json.loads((output / 'david-guetta.json').read_text())
        self.assertEqual(old['profile_metadata'], current['profile_metadata'])
        self.assertEqual([2025, 2026], [r['year'] for r in current['rankings']])
        profile_source = old['sources'][1]
        preserved = [s for s in current['sources'] if s['retrieved_at'] == profile_source['retrieved_at']]
        self.assertEqual(1, len(preserved))
        self.assertIn('/profile_metadata', preserved[0]['fields'])
        self.assertIn('/origin', preserved[0]['fields'])
        self.assertNotIn('/rankings', preserved[0]['fields'])
        self.assertTrue(any(s['url'] == old['rankings'][0]['source_url'] and '/rankings' in s['fields'] for s in current['sources']))
        latest = current['sources'][-1]
        self.assertIn('/rankings', latest['fields'])
        self.assertNotIn('/image', latest['fields'])

    def test_unchanged_rank_retains_explicit_verified_previous_rank_and_attribution(self):
        old = json.loads((ROOT / 'data/djs/david-guetta.json').read_text())
        old['rankings'][0]['previous_rank'] = 7
        old['sources'][0]['fields'].append('/rankings')
        current = self.refresh(old)
        self.assertEqual(7, current['rankings'][0]['previous_rank'])
        self.assertTrue(any(s['retrieved_at'] == old['sources'][0]['retrieved_at'] and '/rankings' in s['fields'] for s in current['sources']))

    def test_new_edition_retains_original_facts_metadata_and_source_dates(self):
        old = json.loads((ROOT / 'data/djs/david-guetta.json').read_text().replace('2026', '2025'))
        current = self.refresh(old)
        self.assertEqual(old['profile_metadata'], current['profile_metadata'])
        self.assertEqual(old['origin'], current['origin'])
        self.assertEqual(old['styles'], current['styles'])
        self.assertTrue(any(s['retrieved_at'] == old['sources'][1]['retrieved_at'] and '/origin' in s['fields'] for s in current['sources']))
        self.assertTrue(any('/profile_metadata' in s['fields'] and '/2025/' in s['url'] for s in current['sources']))
        self.assertEqual([2025, 2026], [r['year'] for r in current['rankings']])

    def test_changed_rank_does_not_carry_previous_rank_or_infer_one(self):
        old = json.loads((ROOT / 'data/djs/david-guetta.json').read_text())
        old['rankings'][0]['previous_rank'] = 7
        current = self.refresh(old, rank=2)
        self.assertIsNone(current['rankings'][0]['previous_rank'])

    def test_preserved_image_keeps_old_nested_attribution_and_removes_fresh_claims(self):
        old = {'image': {'url': 'https://example.org/old.jpg'}, 'sources': [dict(url='https://example.org/profile', publisher='Official', retrieved_at='2026-01-01T00:00:00Z', fields=['/image/url'])]}
        current = {'image': old['image'], 'sources': [dict(url='https://djmag.com/top100djs', publisher='DJ Mag', retrieved_at='2026-11-15T00:00:00Z', fields=['/name', '/rankings', '/image', '/image/url'])]}
        sources = sync.refresh_sources(old, current, set(), True)
        self.assertEqual(['/image/url'], sources[0]['fields'])
        self.assertEqual(['/name', '/rankings'], sources[1]['fields'])

    def test_exact_previous_rank_attribution_survives_sorted_history_reindexing(self):
        old = json.loads((ROOT / 'data/djs/david-guetta.json').read_text())
        old['rankings'][0]['previous_rank'] = 7
        old['rankings'].append(dict(year=2025, rank=2, previous_rank=3,
            source_url='https://djmag.com/top100djs/2025/2/david-guetta'))
        for source in old['sources']:
            source['fields'] = [field for field in source['fields'] if field != '/rankings']
        old['sources'].append(dict(url=old['rankings'][0]['source_url'], publisher='DJ Mag', retrieved_at='2026-11-01T00:00:00Z', fields=['/rankings/0/previous_rank']))
        old['sources'].append(dict(url=old['rankings'][1]['source_url'], publisher='DJ Mag', retrieved_at='2025-11-01T00:00:00Z', fields=['/rankings/1/previous_rank']))
        current = self.refresh(old)
        self.assertEqual([3, 7], [rank['previous_rank'] for rank in current['rankings']])
        self.assertTrue(any(s['retrieved_at'] == '2026-11-01T00:00:00Z' and s['fields'] == ['/rankings/1/previous_rank'] for s in current['sources']))
        self.assertTrue(any(s['retrieved_at'] == '2025-11-01T00:00:00Z' and s['fields'] == ['/rankings/0/previous_rank'] for s in current['sources']))
        self.assertTrue(any(s['url'] == current['rankings'][-1]['source_url'] and '/rankings' in s['fields'] for s in current['sources']))


class ProfileCollectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'data/djs').mkdir(parents=True)
        (self.root / 'data/dj.schema.json').write_bytes((ROOT / 'data/dj.schema.json').read_bytes())

    def record(self, identity, year=2026):
        row = json.loads((ROOT / 'data/djs/david-guetta.json').read_text())
        row['description'] = None  # Fixture must not inherit the live profile body.
        row['id'] = identity
        row.pop('profile_metadata', None)
        row.pop('origin', None)
        row.pop('best_known_for', None)
        row['styles'] = []
        row['rankings'] = [dict(year=year, rank=1, previous_rank=None,
            source_url=f'https://djmag.com/top100djs/{year}/1/{identity}')]
        path = self.root / 'data/djs' / f'{identity}.json'
        path.write_text(json.dumps(row))
        return path

    def profile_html(self, identity, year=2026):
        return '<div class="field--name-field-intro"><p><strong>From: </strong>France</p></div><script type="application/ld+json">' + json.dumps({
            '@type': 'Article', 'mainEntityOfPage': f'https://djmag.com/top100djs/{year}/1/{identity}'}) + '</script>'

    def collect(self, responses, budget=1000):
        with patch.object(enrich, 'ROOT', self.root), patch.object(enrich, 'fetch', side_effect=['User-agent: *\nAllow: /\n'] + responses) as fetch, patch.object(enrich.time, 'sleep'), patch.object(sys, 'argv', ['enrich', '--max-profiles', str(budget)]), contextlib.redirect_stdout(io.StringIO()):
            enrich.main()
        return fetch

    def test_timeout_fails_after_preserving_successful_checkpoint(self):
        alpha = self.record('alpha')
        beta = self.record('beta')
        previous_beta = beta.read_bytes()
        with self.assertRaisesRegex(RuntimeError, 'incomplete'):
            self.collect([self.profile_html('alpha'), URLError(TimeoutError())])
        self.assertIn('profile_metadata', json.loads(alpha.read_text()))
        self.assertEqual(previous_beta, beta.read_bytes())
        self.assertFalse(list((self.root / 'data/djs').glob('*.tmp')))

    def test_budget_exhaustion_fails_with_checkpoint_and_unprocessed_record_intact(self):
        alpha = self.record('alpha')
        beta = self.record('beta')
        previous_beta = beta.read_bytes()
        with self.assertRaisesRegex(RuntimeError, 'incomplete.*1/2'):
            self.collect([self.profile_html('alpha')], budget=1)
        self.assertIn('profile_metadata', json.loads(alpha.read_text()))
        self.assertEqual(previous_beta, beta.read_bytes())

    def test_no_profiles_fails_before_source_request(self):
        with patch.object(enrich, 'ROOT', self.root), patch.object(enrich, 'fetch') as fetch, patch.object(sys, 'argv', ['enrich']):
            with self.assertRaisesRegex(RuntimeError, 'No .*profiles'):
                enrich.main()
            fetch.assert_not_called()

    def test_success_collects_only_latest_year_and_preserves_historical_only_artist(self):
        historical = self.record('archive', year=2025)
        previous_historical = historical.read_bytes()
        current = self.record('current')
        fetch = self.collect([self.profile_html('current')])
        self.assertEqual(['https://djmag.com/robots.txt', 'https://djmag.com/top100djs/2026/1/current'], [call.args[0] for call in fetch.call_args_list])
        self.assertEqual(previous_historical, historical.read_bytes())
        row = json.loads(current.read_text())
        self.assertEqual('France', row['origin'])
        self.assertEqual([], row['nationalities'])
        self.assertIsNone(row['birth_date'])
        self.assertIsNone(row['description'])

    def test_description_persisted_with_provenance(self):
        current = self.record('current')
        self.collect([self.profile_html('current') + '<div class="field--name-body"><p>Full profile.</p><p>Last paragraph.</p></div>'])
        row = json.loads(current.read_text())
        self.assertEqual('Full profile.\n\nLast paragraph.', row['description'])
        self.assertIn('/description', row['sources'][-1]['fields'])
        self.assertNotIn('description', row['profile_metadata'])

    def test_missing_body_preserves_prior_description_and_provenance_but_fails_acceptance(self):
        current = self.record('current')
        row = json.loads(current.read_text())
        row['description'] = 'Earlier verified description.'
        row['sources'].append(dict(url=row['rankings'][0]['source_url'], publisher='DJ Mag', retrieved_at='2026-01-01T00:00:00Z', fields=['/description']))
        current.write_text(json.dumps(row))
        with self.assertRaisesRegex(RuntimeError, 'Description extraction incomplete'):
            self.collect([self.profile_html('current')])
        updated = json.loads(current.read_text())
        self.assertEqual(row['description'], updated['description'])
        self.assertIn(row['sources'][-1], updated['sources'])
        self.assertNotIn('/description', updated['sources'][-1]['fields'])

    def test_missing_body_does_not_claim_new_description_evidence(self):
        current = self.record('current')
        self.collect([self.profile_html('current')])
        updated = json.loads(current.read_text())
        self.assertIsNone(updated['description'])
        self.assertNotIn('/description', updated['sources'][-1]['fields'])

    def test_invalid_profile_fails_without_replacing_existing_record(self):
        current = self.record('current')
        previous = current.read_bytes()
        with self.assertRaisesRegex(ValueError, 'Unexpected profile structure'):
            self.collect(['<h1>Access challenge</h1>'])
        self.assertEqual(previous, current.read_bytes())
        self.assertFalse(list((self.root / 'data/djs').glob('*.tmp')))

    def test_policy_denial_propagates_and_preserves_record_without_retry(self):
        current = self.record('current')
        previous = current.read_bytes()
        with patch.object(enrich, 'ROOT', self.root), patch.object(enrich, 'fetch', side_effect=['User-agent: *\nAllow: /\n', URLError('network-policy denied')]) as fetch, patch.object(enrich.time, 'sleep'), patch.object(sys, 'argv', ['enrich']):
            with self.assertRaisesRegex(URLError, 'network-policy denied'):
                enrich.main()
        self.assertEqual(2, fetch.call_count)
        self.assertEqual(previous, current.read_bytes())

    def test_existing_metadata_does_not_count_as_fetched_this_run(self):
        current = self.record('current')
        row = json.loads(current.read_text())
        row['profile_metadata'] = json.loads((ROOT / 'data/djs/david-guetta.json').read_text())['profile_metadata']
        current.write_text(json.dumps(row))
        with self.assertRaisesRegex(RuntimeError, 'incomplete.*0/1'):
            self.collect([URLError(TimeoutError())])

    def test_checkpoint_replace_failure_preserves_original_bytes(self):
        current = self.record('current')
        previous = current.read_bytes()
        with patch.object(Path, 'replace', side_effect=OSError('simulated replacement failure')):
            with self.assertRaisesRegex(OSError, 'replacement failure'):
                self.collect([self.profile_html('current')])
        self.assertEqual(previous, current.read_bytes())

    def test_enrichment_retains_sourced_previous_rank_without_new_rank_or_image_claim(self):
        current = self.record('current')
        row = json.loads(current.read_text())
        row['rankings'][0]['previous_rank'] = 7
        row['sources'] = [dict(url=row['rankings'][0]['source_url'], publisher='DJ Mag', retrieved_at='2026-11-01T00:00:00Z', fields=['/rankings/0/previous_rank', '/image'])]
        previous_image = row['image']
        current.write_text(json.dumps(row))
        self.collect([self.profile_html('current')])
        collected = json.loads(current.read_text())
        self.assertEqual(7, collected['rankings'][0]['previous_rank'])
        self.assertEqual(previous_image, collected['image'])
        self.assertEqual(row['sources'][0], collected['sources'][0])
        self.assertNotIn('/rankings', collected['sources'][-1]['fields'])
        self.assertNotIn('/image', collected['sources'][-1]['fields'])

    def test_changed_image_does_not_inherit_old_image_rights_metadata(self):
        current = self.record('current')
        row = json.loads(current.read_text())
        row['image']['credit'] = 'Old photo credit'
        row['image']['license'] = 'Old photo license'
        row['image']['license_url'] = 'https://example.org/old-license'
        current.write_text(json.dumps(row))
        html = self.profile_html('current').replace('"@type": "Article"', '"@type": "Article", "image": {"url": "https://djmag.com/new.jpg"}')
        self.collect([html])
        image = json.loads(current.read_text())['image']
        self.assertEqual('https://djmag.com/new.jpg', image['url'])
        self.assertEqual(row['rankings'][0]['source_url'], image['source_url'])
        self.assertIsNone(image['credit'])
        self.assertIsNone(image['license'])
        self.assertIsNone(image['license_url'])

    def test_verified_image_can_populate_previously_missing_image(self):
        current = self.record('current')
        row = json.loads(current.read_text())
        row['image'] = None
        current.write_text(json.dumps(row))
        html = self.profile_html('current').replace('"@type": "Article"', '"@type": "Article", "image": {"url": "https://djmag.com/new.jpg"}')
        self.collect([html])
        collected = json.loads(current.read_text())
        self.assertEqual(dict(url='https://djmag.com/new.jpg', source_url=row['rankings'][0]['source_url'], credit=None, license=None, license_url=None), collected['image'])
        self.assertIn('/image', collected['sources'][-1]['fields'])

    def test_changed_profile_facts_drop_old_claims_but_keep_unchanged_attribution(self):
        current = self.record('current')
        row = json.loads(current.read_text())
        row.update(origin='France', styles=['House'], best_known_for='Old fact', nationalities=['France'])
        row['sources'] = [dict(url=row['rankings'][0]['source_url'], publisher='DJ Mag', retrieved_at='2026-11-01T00:00:00Z', fields=['/origin', '/styles', '/best_known_for', '/nationalities'])]
        current.write_text(json.dumps(row))
        self.collect([self.profile_html('current').replace('>France<', '>United Kingdom<')])
        collected = json.loads(current.read_text())
        self.assertEqual('United Kingdom', collected['origin'])
        self.assertEqual([], collected['styles'])
        self.assertIsNone(collected['best_known_for'])
        self.assertEqual(dict(row['sources'][0], fields=['/nationalities']), collected['sources'][0])
        self.assertIn('/origin', collected['sources'][-1]['fields'])


if __name__ == '__main__':
    unittest.main()
