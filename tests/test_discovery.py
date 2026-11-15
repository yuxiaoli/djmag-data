import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/'scripts'))
from discover import current_year_links
class ScopeTests(unittest.TestCase):
 def test_no_archives(self):
  links=current_year_links('<a href="/top100djs/2025">old</a><a href="/top100djs/2026/101/example">new</a>',2026)
  self.assertEqual(['https://djmag.com/top100djs/2026/101/example'],links)
 def test_no_other_hosts(self):self.assertEqual([],current_year_links('<a href="https://evil.example/top100djs/2026">bad</a>',2026))
