import importlib.util
from pathlib import Path
import unittest
spec=importlib.util.spec_from_file_location('sync',Path(__file__).parents[1]/'scripts/sync.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class ParserTests(unittest.TestCase):
 def fixture(self,n=100):return ''.join(f'<a href="/top100djs/2025/{i}/example-{i}">Example {i}</a>' for i in range(1,n+1))
 def test_complete(self):
  rows=m.parse_rankings(self.fixture(),'2026-11-15T00:00:00Z');self.assertEqual(100,len(rows));self.assertEqual(2025,rows[0]['rankings'][0]['year']);self.assertIsNone(rows[0]['birth_date'])
 def test_current_over_100(self):
  self.assertEqual(101,len(m.parse_rankings(self.fixture(101),'2026-11-15T00:00:00Z')))
 def test_latest_only(self):
  self.assertEqual(100,len(m.parse_rankings(self.fixture()+self.fixture().replace('/2025/','/2024/'),'2026-11-15T00:00:00Z')))
 def test_incomplete(self):
  with self.assertRaises(ValueError):m.parse_rankings(self.fixture(99),'2026-11-15T00:00:00Z')
 def test_empty(self):
  with self.assertRaises(ValueError):m.parse_rankings('<h1>Challenge</h1>','2026-11-15T00:00:00Z')
 def test_duplicate_links(self):self.assertEqual(100,len(m.parse_rankings(self.fixture()*2,'2026-11-15T00:00:00Z')))
if __name__=='__main__':unittest.main()
