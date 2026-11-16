from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ('annual.yml', 'venues-annual.yml', 'pages.yml')


class PublicationContractTests(unittest.TestCase):
    def test_catalog_publications_share_non_canceling_max_queue(self):
        for name in WORKFLOWS:
            with self.subTest(workflow=name):
                text = (ROOT / '.github/workflows' / name).read_text()
                block = re.search(r'^concurrency:\n((?:[ \t]+[^\n]*\n)+)', text, re.M)
                self.assertIsNotNone(block)
                self.assertRegex(block[1], r'(?m)^  group: catalog-publish$')
                self.assertRegex(block[1], r'(?m)^  cancel-in-progress: false$')
                self.assertRegex(block[1], r'(?m)^  queue: max$')

    def test_each_publication_checks_out_develop_and_builds_both_catalogs_before_upload(self):
        for name in WORKFLOWS:
            with self.subTest(workflow=name):
                text = (ROOT / '.github/workflows' / name).read_text()
                self.assertRegex(text, r'uses: actions/checkout@v4\n        with:\n          ref: develop\n')
                dj = text.index('run: python scripts/build_site.py')
                venues = text.index('run: python scripts/build_venues.py')
                upload = text.index('uses: actions/upload-pages-artifact@v3')
                deploy = text.index('uses: actions/deploy-pages@v4')
                self.assertLess(dj, upload)
                self.assertLess(venues, upload)
                self.assertLess(upload, deploy)
                self.assertNotIn('continue-on-error:', text)
                self.assertNotRegex(text, r'if:\s*(?:\$\{\{\s*)?always\(')
                if name != 'pages.yml':
                    collector = 'sync_venues.py' if name == 'venues-annual.yml' else 'enrich_profiles.py --max-profiles 1000'
                    self.assertLess(text.index('run: python scripts/' + collector), text.index('git push origin HEAD:develop'))
                    self.assertLess(text.index('git push origin HEAD:develop'), min(dj, venues))


if __name__ == '__main__':
    unittest.main()
