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

class BiographyTests(unittest.TestCase):
 def test_full_nested_body_and_excluded_chrome(self):
  html='<nav>Menu</nav><div class="field field--name-body"><div><p>First <em>full</em> paragraph &amp; facts.</p><p>Second paragraph.</p><aside>Ad</aside><script>bad()</script><p>Final paragraph.</p></div></div><footer>Subscribe</footer>'
  self.assertEqual(parse_profile(html)['description'],'First full paragraph & facts.\n\nSecond paragraph.\n\nFinal paragraph.')
 def test_jsonld_full_body_not_short_description(self):
  import json
  html='<script type="application/ld+json">'+json.dumps({'@type':'Article','articleBody':'Full first paragraph.\nSecond paragraph.','description':'Teaser'})+'</script>'
  self.assertEqual(parse_profile(html)['description'],'Full first paragraph.\n\nSecond paragraph.')
 def test_absent_body_is_unknown(self):
  self.assertIsNone(parse_profile('<meta name="description" content="Teaser"><p>Unscoped unrelated text</p>')['description'])
 def test_empty_body_does_not_invent(self):
  self.assertIsNone(parse_profile('<div class="field--name-body"><iframe src="video"></iframe></div>')['description'])
 def test_inline_spacing_and_duplicate_responsive_body(self):
  b='<div itemprop="articleBody"><p>A <strong>long</strong> body.</p></div>'
  self.assertEqual(parse_profile(b+b)['description'],'A long body.')
