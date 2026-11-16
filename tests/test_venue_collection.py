import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import URLError
from jsonschema import ValidationError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import sync_venues as collector


class VenueCollectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'data/venues').mkdir(parents=True)
        (self.root / 'data/venue.schema.json').write_bytes((ROOT / 'data/venue.schema.json').read_bytes())
        external = json.loads((ROOT / 'data/venues/omnia-nightclub.json').read_text())
        external['source']['listing_url'] = 'https://example.org/manually-reviewed-venues'
        (self.root / 'data/venues/omnia-nightclub.json').write_text(json.dumps(external))
        (self.root / 'data/venues/manual.json').write_text('{"manual": "retain unknown schema bytes"}')

    def snapshot(self):
        return {path.name: path.read_bytes() for path in (self.root / 'data/venues').iterdir()}

    def directory(self, *identities):
        return ''.join(f'<a href="{collector.BASE}/venues/{identity}/">Club Details</a>' for identity in identities)

    def detail(self, name):
        return f'<h1>{name}</h1><p><strong>Location:</strong> Example hotel</p>'

    def run_collector(self, responses):
        with patch.object(collector, 'ROOT', self.root), patch.object(collector, 'fetch', side_effect=responses) as fetch, patch.object(collector.time, 'sleep') as sleep, contextlib.redirect_stdout(io.StringIO()):
            self.last_fetch = fetch
            collector.run()
        return fetch, sleep

    def test_duplicate_ids_across_categories_fail_before_record_replacement(self):
        previous = self.snapshot()
        responses = ['User-agent: *\nAllow: /', self.directory('same'), self.directory('same'), self.detail('Same'), self.detail('Same')]
        with self.assertRaisesRegex(ValueError, 'Duplicate venue'):
            self.run_collector(responses)
        self.assertEqual(previous, self.snapshot())

    def test_fetch_or_parse_failure_preserves_snapshot_without_retry(self):
        previous = self.snapshot()
        for failure in (URLError('network policy denied'), '<h2>Missing venue heading</h2>'):
            with self.subTest(failure=type(failure).__name__):
                responses = ['User-agent: *\nAllow: /', self.directory('alpha'), self.directory('beta'), self.detail('Alpha'), failure]
                with self.assertRaises((URLError, ValueError)):
                    self.run_collector(responses)
                self.assertEqual(5, self.last_fetch.call_count)
                self.assertEqual(previous, self.snapshot())

    def test_schema_failure_preserves_snapshot(self):
        previous = self.snapshot()
        responses = ['User-agent: *\nAllow: /', self.directory('alpha'), self.directory('beta'), self.detail('Alpha'), self.detail('Beta')]
        original = collector.extract
        def invalid_second(markup, url, category, observed):
            record = original(markup, url, category, observed)
            if record['id'] == 'beta':
                record['name'] = ''
            return record
        with patch.object(collector, 'extract', side_effect=invalid_second), self.assertRaises(ValidationError):
            self.run_collector(responses)
        self.assertEqual(previous, self.snapshot())

    def test_robots_denial_stops_before_any_directory_request_or_write(self):
        previous = self.snapshot()
        with self.assertRaisesRegex(RuntimeError, 'Robots denies directory'):
            self.run_collector(['User-agent: *\nDisallow: /'])
        self.assertEqual(1, self.last_fetch.call_count)
        self.assertEqual(previous, self.snapshot())

    def test_successful_refresh_honors_combined_robots_delay_and_keeps_existing_records(self):
        previous = self.snapshot()
        responses = ['User-agent: *\nAllow: /\nCrawl-delay: 30\nRequest-rate: 1/60', self.directory('alpha'), self.directory('beta'), self.detail('Alpha'), self.detail('Beta')]
        fetch, sleep = self.run_collector(responses)
        self.assertEqual(5, fetch.call_count)
        self.assertEqual([60, 60, 60, 60], [call.args[0] for call in sleep.call_args_list])
        self.assertEqual({}, fetch.call_args_list[0].kwargs)
        policy = fetch.call_args_list[1].kwargs['robots']
        for call in fetch.call_args_list[1:]:
            self.assertEqual(60, call.kwargs['redirect_delay'])
            self.assertIs(policy, call.kwargs['robots'])
            self.assertTrue(policy.can_fetch(collector.AGENT, call.args[0]))
        self.assertEqual(previous['omnia-nightclub.json'], self.snapshot()['omnia-nightclub.json'])
        self.assertEqual('nightclub', json.loads((self.root / 'data/venues/alpha.json').read_text())['listing_category'])
        self.assertEqual('dayclub', json.loads((self.root / 'data/venues/beta.json').read_text())['listing_category'])
        self.assertFalse(list((self.root / 'data/venues').glob('*.tmp')))

    def test_shrunken_directory_preserves_all_bytes_and_reports_missing_known_identity(self):
        known = collector.extract(self.detail('Known alpha'), collector.BASE + '/venues/alpha/', 'nightclub', '2026-11-15T00:00:00Z')
        known['source']['listing_url'] = collector.BASE + '/nightclubs/'
        (self.root / 'data/venues/alpha.json').write_text(json.dumps(known))
        previous = self.snapshot()
        responses = ['User-agent: *\nAllow: /', self.directory('beta'), self.directory('gamma'), self.detail('Beta'), self.detail('Gamma')]
        with self.assertRaisesRegex(ValueError, 'missing.*alpha.*nightclub'):
            self.run_collector(responses)
        self.assertEqual(previous, self.snapshot())
        self.assertEqual(3, self.last_fetch.call_count)

    def test_h1_only_challenge_cannot_replace_venue_data(self):
        previous = self.snapshot()
        responses = ['User-agent: *\nAllow: /', self.directory('alpha'), self.directory('beta'), self.detail('Alpha'), '<h1>Just a moment</h1>']
        with self.assertRaisesRegex(ValueError, 'Unexpected venue profile structure'):
            self.run_collector(responses)
        self.assertEqual(previous, self.snapshot())

    def test_same_id_with_changed_source_url_or_category_requires_review(self):
        known = collector.extract(self.detail('Known alpha'), collector.BASE + '/venues/alpha/', 'nightclub', '2026-11-15T00:00:00Z')
        known['source']['listing_url'] = collector.BASE + '/nightclubs/'
        (self.root / 'data/venues/alpha.json').write_text(json.dumps(known))
        previous = self.snapshot()
        changed_url = self.directory('alpha').replace('/venues/alpha/', '/nightclubs/alpha/')
        for nightclubs, dayclubs in ((changed_url, self.directory('beta')), (self.directory('beta'), self.directory('alpha'))):
            with self.subTest(directory=nightclubs):
                with self.assertRaisesRegex(ValueError, 'missing.*alpha.*nightclub'):
                    self.run_collector(['User-agent: *\nAllow: /', nightclubs, dayclubs])
                self.assertEqual(previous, self.snapshot())
                self.assertEqual(3, self.last_fetch.call_count)

    def test_complete_known_baseline_can_refresh_while_unrelated_records_are_preserved(self):
        known = collector.extract(self.detail('Known alpha'), collector.BASE + '/venues/alpha/', 'nightclub', '2026-11-15T00:00:00Z')
        known['source']['listing_url'] = collector.BASE + '/nightclubs/'
        (self.root / 'data/venues/alpha.json').write_text(json.dumps(known))
        previous = self.snapshot()
        self.run_collector(['User-agent: *\nAllow: /', self.directory('alpha'), self.directory('beta'), self.detail('Alpha updated'), self.detail('Beta')])
        self.assertEqual('Alpha updated', json.loads((self.root / 'data/venues/alpha.json').read_text())['name'])
        self.assertEqual(previous['manual.json'], self.snapshot()['manual.json'])
        self.assertEqual(previous['omnia-nightclub.json'], self.snapshot()['omnia-nightclub.json'])


if __name__ == '__main__':
    unittest.main()
