import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/'scripts'))
from profile import parse_profile
class ProfileTests(unittest.TestCase):
 def test_labels_and_publisher(self):
  html='''<div class="field--name-field-intro"><p><strong>From: </strong>Exampleland</p><p><strong>DJ style: </strong>House, techno.</p></div><span class="entry-header__movement-text">Up</span><div class="field--name-field-top-100-places">3</div><script type="application/ld+json">{"@graph":[{"@type":"Article","author":{"name":"Publisher","sameAs":["https://example.org/not-artist"]},"mainEntityOfPage":"https://example.org/artist"}]}</script>'''
  p=parse_profile(html);self.assertEqual(3,p['movement_places']);self.assertEqual('Exampleland',p['intro_fields'][0]['value']);self.assertNotIn('sameAs',str(p));self.assertIsNone(p['article']['modified_at'])
 def test_unknown_fields(self):
  p=parse_profile('<div class="field--name-field-intro"><p><strong>New field: </strong>New fact</p></div>');self.assertEqual('New field',p['intro_fields'][0]['label']);self.assertIsNone(p['movement'])
