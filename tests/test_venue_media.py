import sys,unittest,json,tempfile,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from build_venues import youtube_embed,safe_url,photo,build
class MediaTests(unittest.TestCase):
 def test_embed_allowlist(self):
  self.assertEqual(youtube_embed('https://www.youtube.com/embed/UAGuJJF2KDo'),'https://www.youtube.com/embed/UAGuJJF2KDo')
  for url in ['https://evil.example/embed/UAGuJJF2KDo','javascript:alert(1)','https://youtube.com/embed/../../bad','http://youtube.com/embed/UAGuJJF2KDo']:
   self.assertIsNone(youtube_embed(url))
 def test_image_fallback_and_escaping(self):
  self.assertIn('Venue image unavailable',photo(None,'test'))
  s=photo('https://images.example/a.jpg','<name>');self.assertIn('&lt;name&gt;',s);self.assertIn("classList.add",s)
 def test_schemes(self):
  self.assertIsNone(safe_url('javascript:alert(1)'));self.assertIsNone(safe_url('//unverified.example/image'))
 def test_source_records_unchanged_and_fallback_links(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp);(p/'assets').mkdir();(p/'assets/venues.css').write_text('');(p/'data/venues').mkdir(parents=True)
   record={'id':'test','name':'Test','listing_category':'nightclub','description':'Venue','facts':{},'links':[{'kind':'image','url':'https://example.com/a.jpg'},{'kind':'video','url':'https://www.youtube.com/embed/UAGuJJF2KDo'}],'source':{'url':'https://example.com','observed_at':'2026-11-15'}}
   f=p/'data/venues/test.json';f.write_text(json.dumps(record));before=f.read_bytes();build(p);self.assertEqual(f.read_bytes(),before)
   output=(p/'site/venues/test.html').read_text();self.assertIn('<img ',output);self.assertIn('<iframe ',output);self.assertIn('Open original photo',output);self.assertIn('Watch video on YouTube',output)
