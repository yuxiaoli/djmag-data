import json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from build_venues import build
class BuildTest(unittest.TestCase):
 def test_isolation_escaping(self):
  with tempfile.TemporaryDirectory() as temp:
   p=Path(temp);(p/'data/venues').mkdir(parents=True);(p/'site').mkdir();(p/'site/index.html').write_text('DJ unchanged')
   d={'id':'test','name':'<unsafe>','listing_category':'nightclub','description':None,'facts':{},'links':[],'source':{'url':'https://nocovernightclubs.com/test','observed_at':'2026-11-15'}}
   (p/'data/venues/test.json').write_text(json.dumps(d));self.assertEqual(build(p),1)
   self.assertEqual((p/'site/index.html').read_text(),'DJ unchanged');self.assertIn('&lt;unsafe&gt;',(p/'site/venues/test.html').read_text())
   index=json.loads((p/'site/data/venues/index.json').read_text());self.assertEqual(index['venues'][0]['id'],'test')
