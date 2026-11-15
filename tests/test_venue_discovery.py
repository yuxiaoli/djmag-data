import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from sync_venues import discover,fetch
class DiscoveryTests(unittest.TestCase):
 def test_details_only_and_dedup(self):
  html='<a href="https://example.test/a">Club Details</a><a href="https://example.test/a">Club Details</a><a href="https://example.test/b">Guest List</a>'
  self.assertEqual(discover(html),['https://example.test/a'])

 def test_external_url_rejected_before_network(self):
  with self.assertRaises(ValueError):fetch("https://example.test/")
