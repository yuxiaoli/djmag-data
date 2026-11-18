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
   css=(root/'site/style.css').read_text()
   self.assertIn('.ranking-label,.profile-facts dt,.profile-details dt,.profile-details h2{color:#9eabc1;font-size:16px;font-weight:400;line-height:1.55;letter-spacing:normal;margin:12px 0 0}',css)
   self.assertIn('.big{font-size:16px;font-weight:400;line-height:1.55;margin:0}',css)
   self.assertEqual(html.count('Current Ranking'),1)
   self.assertEqual(html.count('#'+str(row['rankings'][-1]['rank'])),1)
   self.assertNotIn('<h2>Current ranking</h2>',html)
   self.assertNotIn('Birth date</dt>',html)
   self.assertNotIn('Gender</dt>',html)
   self.assertNotIn('original DJ Mag profile',html);self.assertNotIn('Source:',html);self.assertNotIn('Source profile fields',html)
   self.assertNotIn('href="https://djmag.com',html)
   self.assertEqual(row['sources'],json.loads((root/'site/data/djs/david-guetta.json').read_text())['sources'])

 def test_populated_secondary_facts_preserved_under_details(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);shutil.copytree(ROOT/'scripts',root/'scripts');shutil.copytree(ROOT/'data',root/'data')
   p=root/'data/djs/david-guetta.json';row=json.loads(p.read_text());row['birth_date']='1967-11-07';row['gender']='Male';p.write_text(json.dumps(row))
   subprocess.run([sys.executable,str(root/'scripts/build_site.py')],check=True,capture_output=True)
   html=(root/'site/djs/david-guetta.html').read_text()
   for label,value in [('Birth date','1967-11-07'),('Gender','Male')]:
    self.assertIn('<dt>'+label+'</dt><dd>'+value+'</dd>',html)
    self.assertGreater(html.index(label+'</dt>'),html.index('<h2>Profile details</h2>'))
   self.assertEqual(row,json.loads((root/'site/data/djs/david-guetta.json').read_text()))
