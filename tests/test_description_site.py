import json,shutil,subprocess,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class DescriptionSiteTests(unittest.TestCase):
 def test_render_full_body_escaped_and_keep_internal_provenance(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);shutil.copytree(ROOT/'scripts',root/'scripts');shutil.copytree(ROOT/'data',root/'data')
   p=root/'data/djs/david-guetta.json';row=json.loads(p.read_text());row['description']='First <unsafe> & paragraph.\n\nLast paragraph.';p.write_text(json.dumps(row))
   subprocess.run([sys.executable,str(root/'scripts/build_site.py')],check=True,capture_output=True)
   html=(root/'site/djs/david-guetta.html').read_text()
   self.assertIn('<p>First &lt;unsafe&gt; &amp; paragraph.</p><p>Last paragraph.</p>',html)
   self.assertLess(html.index('From</dt>'),html.index('DJ style</dt>'))
   self.assertLess(html.index('DJ style</dt>'),html.index('Best known for</dt>'))
   self.assertLess(html.index('Best known for</dt>'),html.index('Ranking change</dt>'))
   self.assertLess(html.index('Ranking change</dt>'),html.index('<h2>Profile details</h2>'))
   self.assertLess(html.index('<h2>Profile details</h2>'),html.index('First &lt;unsafe&gt;'))
   self.assertLess(html.index('Last paragraph.'),html.index('</section>'))
   self.assertEqual(html.count('First &lt;unsafe&gt;'),1)
   self.assertNotIn('original DJ Mag profile',html);self.assertNotIn('Source:',html);self.assertNotIn('Source profile fields',html)
   self.assertNotIn('href="https://djmag.com',html)
   self.assertEqual(row['sources'],json.loads((root/'site/data/djs/david-guetta.json').read_text())['sources'])
