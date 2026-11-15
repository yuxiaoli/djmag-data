import sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from venue import extract
class VenueTests(unittest.TestCase):
 def test_boundaries(self):
  d=extract('<h1>One &amp; Two</h1><p><strong>Location:</strong> Hotel</p><iframe src="https://www.youtube.com/embed/abc"></iframe><h2>Upcoming Events</h2><a href="https://wrong.example/">Other venue</a>','https://nocovernightclubs.com/nightclubs/test/','nightclub','2026-11-16T00:00:00Z')
  self.assertEqual(d['name'],'One & Two'); self.assertEqual(d['facts']['location'],'Hotel');self.assertEqual(len(d['links']),1);self.assertEqual(d['description'],'One & Two at Hotel.')
 def test_host(self):
  with self.assertRaises(ValueError):extract('<h1>Test</h1>','https://wrong.example/','nightclub','')
 def test_missing_heading(self):
  with self.assertRaises(ValueError):extract('No heading','https://nocovernightclubs.com/test','nightclub','')
if __name__=='__main__':unittest.main()
