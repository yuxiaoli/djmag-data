import json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from build_venues import build
class BuildTest(unittest.TestCase):
 def test_reviewed_conflicts_keep_their_own_observation_date_and_are_escaped(self):
  with tempfile.TemporaryDirectory() as temp:
   p=Path(temp);(p/'assets').mkdir();(p/'assets/venues.css').write_text('body{}');(p/'data/venues').mkdir(parents=True)
   d={'id':'test','name':'Test venue','listing_category':'nightclub','description':None,'facts':{},'links':[],'source':{'url':'https://nocovernightclubs.com/test','observed_at':'2026-11-16T07:14:49Z'},'quality':{'source_conflicts':['Directory says Thursday; profile says Friday. <review>'],'source_conflicts_observed_at':'2026-11-15T18:25:43Z'}}
   (p/'data/venues/test.json').write_text(json.dumps(d));build(p)
   output=(p/'site/venues/test.html').read_text()
   self.assertIn('Source review notes',output)
   self.assertIn('Review source observed 2026-11-15T18:25:43Z',output)
   self.assertIn('Directory says Thursday; profile says Friday. &lt;review&gt;',output)
   self.assertNotIn('<review>',output)
   self.assertIn('Observed 2026-11-16T07:14:49Z',output)
 def test_isolation_escaping(self):
  with tempfile.TemporaryDirectory() as temp:
   p=Path(temp);(p/'assets').mkdir();(p/'assets/venues.css').write_text('body{}');(p/'data/venues').mkdir(parents=True);(p/'site').mkdir();(p/'site/index.html').write_text('DJ unchanged')
   d={'id':'test','name':'<unsafe>','listing_category':'nightclub','description':None,'facts':{},'links':[],'source':{'url':'https://nocovernightclubs.com/test','observed_at':'2026-11-15'}}
   (p/'data/venues/test.json').write_text(json.dumps(d));self.assertEqual(build(p),1)
   self.assertEqual((p/'site/index.html').read_text(),'DJ unchanged');self.assertIn('&lt;unsafe&gt;',(p/'site/venues/test.html').read_text())
   index=json.loads((p/'site/data/venues/index.json').read_text());self.assertEqual(index['venues'][0]['id'],'test')

 def test_localized_details_link_to_both_languages_and_publish_the_localized_json(self):
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        (root / 'assets').mkdir()
        (root / 'assets/venues.css').write_text('body{}', encoding='utf-8')
        record = {
            'id': 'test',
            'name': 'Test venue',
            'listing_category': 'nightclub',
            'description': 'Source description.',
            'facts': {'nights': 'Friday'},
            'links': [],
            'source': {'url': 'https://example.com/test', 'observed_at': '2026-11-15T12:00:00Z'},
        }
        localized = dict(record, description='简中简介 <测试>。', facts={'nights': '周五'})
        for language, data in [('en', record), ('zh-CN', localized)]:
            folder = root / 'data/venues' / language
            folder.mkdir(parents=True)
            (folder / 'test.json').write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')

        self.assertEqual(build(root), 1)
        site = root / 'site'
        english = (site / 'venues/test.html').read_text(encoding='utf-8')
        chinese = (site / 'venues/zh-CN/test.html').read_text(encoding='utf-8')
        catalog = (site / 'venues/zh-CN/index.html').read_text(encoding='utf-8')
        self.assertIn('href="zh-CN/test.html" lang="zh-CN"', english)
        self.assertIn('href="../test.html" lang="en"', chinese)
        self.assertIn('<html lang="zh-CN">', chinese)
        self.assertIn('简中简介 &lt;测试&gt;。', chinese)
        self.assertIn('<dt>夜间营业日</dt><dd>周五</dd>', chinese)
        self.assertIn('href="test.html"', catalog)
        self.assertIn('href="../../data/venues/zh-CN/test.json"', chinese)
        self.assertEqual(
            (site / 'data/venues/zh-CN/test.json').read_bytes(),
            (root / 'data/venues/zh-CN/test.json').read_bytes(),
        )
        self.assertEqual(
            (site / 'data/venues/en/test.json').read_bytes(),
            (site / 'data/venues/test.json').read_bytes(),
        )
