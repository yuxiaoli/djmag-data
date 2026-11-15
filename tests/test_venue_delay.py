import sys,unittest,urllib.robotparser
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from sync_venues import crawl_delay
class RobotsDelay(unittest.TestCase):
 def test_floor(self):
  p=urllib.robotparser.RobotFileParser();p.parse(['User-agent: *','Allow: /']);self.assertEqual(crawl_delay(p),10)
 def test_declared(self):
  p=urllib.robotparser.RobotFileParser();p.parse(['User-agent: *','Crawl-delay: 30']);self.assertEqual(crawl_delay(p),30)
 def test_rate(self):
  p=urllib.robotparser.RobotFileParser();p.parse(['User-agent: *','Request-rate: 1/60']);self.assertEqual(crawl_delay(p),60)
