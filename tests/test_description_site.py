import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from html import escape
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class PageTags(HTMLParser):
    def __init__(self, markup):
        super().__init__()
        self.tags = []
        self.feed(markup)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


def plain_headings_and_terms(markup):
    return re.sub(r'<(dt|dd|h2)(?:\s+[^>]*)?>', r'<\1>', markup)


class DescriptionSiteTests(unittest.TestCase):
 def test_render_full_body_escaped_and_keep_internal_provenance(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);self.copy_build_inputs(root)
   p=root/'data/djs/en/david-guetta.json';row=json.loads(p.read_text(encoding='utf-8'));row['description']='First <unsafe> & paragraph.\n\nLast paragraph.';row['birth_date']=None;row['gender']=None;p.write_text(json.dumps(row),encoding='utf-8')
   subprocess.run([sys.executable,str(root/'scripts/build_site.py')],check=True,capture_output=True)
   html=(root/'site/djs/david-guetta.html').read_text(encoding='utf-8')
   html = plain_headings_and_terms(html)
   self.assertRegex(html, r'<p>First &lt;unsafe&gt; &amp; paragraph.</p>\s*<p>Last paragraph.</p>')
   self.assertLess(html.index('From</dt>'),html.index('DJ style</dt>'))
   self.assertLess(html.index('DJ style</dt>'),html.index('Best known for</dt>'))
   self.assertLess(html.index('Best known for</dt>'),html.index('Ranking change</dt>'))
   self.assertLess(html.index('Ranking change</dt>'),html.index('<h2>Profile details</h2>'))
   self.assertLess(html.index('<h2>Profile details</h2>'),html.index('First &lt;unsafe&gt;'))
   self.assertLess(html.index('Last paragraph.'),html.index('</section>'))
   self.assertEqual(html.count('First &lt;unsafe&gt;'),1)
   css=(root/'site/style.css').read_text(encoding='utf-8')
   self.assertIn('.ranking-label,.profile-facts dt,.profile-details dt,.profile-details h2{color:#9eabc1;font-size:16px;font-weight:400;line-height:1.55;letter-spacing:normal;margin:12px 0 0}',css)
   self.assertIn('.big{font-size:16px;font-weight:400;line-height:1.55;margin:0}',css)
   self.assertEqual(html.count('Current Ranking'),1)
   self.assertEqual(html.count('>#'+str(row['rankings'][-1]['rank'])+'<'),1)
   self.assertNotIn('<h2>Current ranking</h2>',html)
   self.assertNotIn('Birth date</dt>',html)
   self.assertNotIn('Age</dt>',html)
   self.assertNotIn('dj-age.js',html)
   self.assertNotIn('Gender</dt>',html)
   self.assertNotIn('original DJ Mag profile',html);self.assertNotIn('Source:',html);self.assertNotIn('Source profile fields',html)
   self.assertNotIn('href="https://djmag.com',html)
   self.assertEqual(row['sources'],json.loads((root/'site/data/djs/david-guetta.json').read_text(encoding='utf-8'))['sources'])

 def test_populated_secondary_facts_preserved_under_details(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);self.copy_build_inputs(root)
   p = root / 'data/djs/en/david-guetta.json'
   row = json.loads(p.read_text(encoding='utf-8'))
   row.update(birth_date='1967-11-07', gender='Male')
   row['profile_metadata']['intro_fields'].append({'label': 'Age', 'value': '999'})
   p.write_text(json.dumps(row), encoding='utf-8')
   subprocess.run([sys.executable,str(root/'scripts/build_site.py')],check=True,capture_output=True)
   html=(root/'site/djs/david-guetta.html').read_text(encoding='utf-8')
   plain = plain_headings_and_terms(html)
   for label,value in [('Birth date','1967-11-07'),('Gender','Male')]:
    self.assertRegex(plain, rf'<dt>{label}</dt>\s*<dd>{value}</dd>')
    self.assertGreater(plain.index(label+'</dt>'),plain.index('<h2>Profile details</h2>'))
   self.assertRegex(html, r'<dt\b[^>]*\bhidden\b[^>]*>Age</dt>\s*<dd\b')
   age = next(attrs for tag, attrs in PageTags(html).tags if tag == 'dd' and attrs.get('data-birth-date') == '1967-11-07')
   self.assertIn('hidden', age)
   self.assertIn('<script src="../dj-age.js" defer></script>',html)
   self.assertNotIn('<dd>999</dd>',plain)
   self.assertEqual((root/'site/dj-age.js').read_bytes(),(root/'assets/dj-age.js').read_bytes())
   self.assertEqual(row,json.loads((root/'site/data/djs/david-guetta.json').read_text(encoding='utf-8')))
   legacy=root/'site/data/djs/david-guetta.json'
   localized=root/'site/data/djs/en/david-guetta.json'
   self.assertEqual(p.read_bytes(),localized.read_bytes())
   self.assertEqual(localized.read_bytes(),legacy.read_bytes())
   self.assertIn('href="../data/djs/en/david-guetta.json"',html)
   index=json.loads((root/'site/data/index.json').read_text(encoding='utf-8'))
   artist=next(a for a in index['artists'] if a['id']=='david-guetta')
   self.assertEqual(artist['record_url'],'data/djs/en/david-guetta.json')
   self.assertEqual(artist['detail_url'],'djs/david-guetta.html')
   self.assertFalse((root/'site/data/djs/zh-CN/.gitkeep').exists())


 def test_localized_biography_and_aliases_keep_canonical_paths(self):
  with tempfile.TemporaryDirectory() as tmp:
   root = Path(tmp)
   self.copy_build_inputs(root)
   name = '大卫·例子 <示例> & 朋友'
   english_alias = 'Mixed & Match'
   chinese_alias = '小例子'
   chinese_bio = '中文首段 <unsafe> & 内容。\n\n最后一段。'
   self.write_localized_example(
    root,
    name=name,
    aliases=[
     {'name': english_alias, 'type': 'alternate_name', 'language': 'en'},
     {'name': chinese_alias, 'type': 'nickname', 'language': 'zh-CN'},
    ],
    description=chinese_bio,
    sources=[{
     'url': 'https://example.org/profile',
     'publisher': 'Example Publisher',
     'retrieved_at': '2026-11-15T04:00:00Z',
     'fields': ['/name', '/aliases/0', '/aliases/1', '/description'],
    }],
   )
   self.write_localized_example(root, identity='anyma', name=None, aliases=[], description=None, sources=[])
   fallback_record = root / 'data/djs/en/anyma.json'
   english = json.loads(fallback_record.read_text(encoding='utf-8'))
   english['description'] = 'English fallback biography.'
   fallback_record.write_text(json.dumps(english), encoding='utf-8')
   subprocess.run([sys.executable, str(root / 'scripts/build_site.py')], check=True, capture_output=True)

   output = root / 'site'
   home = (output / 'index.html').read_text(encoding='utf-8')
   self.assert_language_selector(home)
   cards = {
    attrs['href']: json.loads(attrs['data-search'])
    for tag, attrs in PageTags(home).tags
    if tag == 'a' and 'card' in attrs.get('class', '').split()
   }
   for term in ('David Guetta', name, english_alias, chinese_alias):
    self.assertIn(term, cards['djs/david-guetta.html'])
   self.assertIn('Anyma', cards['djs/anyma.html'])
   self.assertNotIn(None, cards['djs/anyma.html'])

   detail = (output / 'djs/david-guetta.html').read_text(encoding='utf-8')
   self.assert_language_selector(detail)
   tags = PageTags(detail).tags
   bios = {attrs['data-bio-language']: attrs for _, attrs in tags if 'data-bio-language' in attrs}
   self.assertEqual(set(bios), {'en', 'zh-CN'})
   self.assertNotIn('hidden', bios['en'])
   self.assertIn('hidden', bios['zh-CN'])
   self.assertIn(escape(name), detail)
   self.assertRegex(detail, r'<span\b[^>]*\blang="en"[^>]*>Mixed &amp; Match</span>')
   self.assertRegex(detail, r'<span\b[^>]*\blang="zh-CN"[^>]*>小例子</span>')
   self.assertIn('中文首段 &lt;unsafe&gt; &amp; 内容。', detail)
   self.assertIn('最后一段。', detail)
   self.assertNotIn('<unsafe>', detail)
   self.assertTrue(any(tag == 'a' and attrs.get('href') == '../data/djs/en/david-guetta.json' for tag, attrs in tags))
   self.assertEqual((output / 'dj-site.js').read_bytes(), (root / 'assets/dj-site.js').read_bytes())

   fallback = (output / 'djs/anyma.html').read_text(encoding='utf-8')
   fallback_tags = PageTags(fallback).tags
   self.assertNotIn('zh-CN', [attrs.get('data-bio-language') for _, attrs in fallback_tags])
   self.assertIn('<p>English fallback biography.</p>', fallback)
   heading = re.search(r'<h1\b[^>]*>(.*?)</h1>', fallback, re.DOTALL)
   self.assertIsNotNone(heading)
   self.assertEqual(re.sub(r'<[^>]+>', '', heading.group(1)).strip(), 'Anyma')

 def test_build_publishes_localized_profile_and_excludes_research_input(self):
  with tempfile.TemporaryDirectory() as tmp:
   root = Path(tmp)
   self.copy_build_inputs(root)
   profile = self.write_localized_example(root)
   research = root / 'data/djmag-research.zh-CN.output.1.json'
   research.write_text('{}', encoding='utf-8')
   subprocess.run([sys.executable, str(root / 'scripts/build_site.py')], check=True, capture_output=True)
   self.assertEqual(profile.read_bytes(), (root / 'site/data/djs/zh-CN/david-guetta.json').read_bytes())
   self.assertFalse((root / 'site/data' / research.name).exists())
   self.assertEqual('{}', research.read_text(encoding='utf-8'))

 def test_build_rejects_invalid_localized_profile_before_output(self):
  cases = (
   ({'id': 'another-dj'}, b'localized ID and filename'),
   ({'updated_at': '2026-02-30T00:00:00Z'}, b'invalid localized profile at /updated_at'),
   ({'aliases': []}, b'source field /aliases/0 has no localized value'),
   ({'sources': []}, b'missing localized sources for /aliases/0, /description, /name'),
  )
  with tempfile.TemporaryDirectory() as tmp:
   root = Path(tmp)
   self.copy_build_inputs(root)
   for changes, message in cases:
    with self.subTest(changes=changes):
     self.write_localized_example(root, **changes)
     result = subprocess.run([sys.executable, str(root / 'scripts/build_site.py')], capture_output=True)
     self.assertNotEqual(result.returncode, 0)
     self.assertIn(message, result.stderr)
     self.assertFalse((root / 'site').exists())

 def assert_language_selector(self, markup):
  tags = PageTags(markup).tags
  controls = [attrs for tag, attrs in tags if tag == 'select' and attrs.get('id') == 'site-language']
  self.assertEqual(len(controls), 1)
  self.assertTrue(any(tag == 'label' and attrs.get('for') == 'site-language' for tag, attrs in tags))

  match = re.search(r'<select\b(?=[^>]*\bid="site-language")[^>]*>(.*?)</select>', markup, re.DOTALL)
  self.assertIsNotNone(match)
  options_markup = match.group(1)
  options = [attrs for tag, attrs in PageTags(options_markup).tags if tag == 'option']
  self.assertEqual([(option.get('value'), option.get('lang')) for option in options], [
   ('en', 'en'),
   ('zh-CN', 'zh-CN'),
  ])
  for locale, label in [('en', 'English'), ('zh-CN', '简体中文')]:
   self.assertRegex(options_markup, rf'<option\b(?=[^>]*\bvalue="{locale}")[^>]*>\s*{label}\s*</option>')

 def copy_build_inputs(self, root):
  for directory in ('scripts', 'data', 'assets'):
   shutil.copytree(ROOT / directory, root / directory)

 def write_localized_example(self, root, identity='david-guetta', **changes):
  record = json.loads((root / 'data/dj.zh-CN.example.json').read_text(encoding='utf-8'))
  record.update({'id': identity, **changes})
  path = root / 'data/djs/zh-CN' / f'{identity}.json'
  path.parent.mkdir(parents=True, exist_ok=True)
  path.write_text(json.dumps(record, ensure_ascii=False), encoding='utf-8')
  return path
