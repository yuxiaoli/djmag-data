"""Add venue pages to the existing DJ catalog without changing artist output."""
import html,json,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def e(v):return html.escape(str(v),quote=True)
def page(title,body):return '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+e(title)+'</title><link rel="stylesheet" href="../style.css"><body><main>'+body+'</main></body></html>'
def build(root=ROOT):
 out=root/'site'; target=out/'venues';target.mkdir(parents=True,exist_ok=True)
 rows=[json.loads(p.read_text()) for p in sorted((root/'data/venues').glob('*.json')) if p.name!='index.json']
 cards=[];index=[]
 for d in rows:
  slug=d['id'];rel='venues/'+slug+'.html'
  index.append({'id':slug,'name':d['name'],'type':d['listing_category'],'detail_url':rel,'json_url':'data/venues/'+slug+'.json'})
  facts=''.join('<dt>'+e(k.replace('_',' ').title())+'</dt><dd>'+e(v)+'</dd>' for k,v in d['facts'].items())
  links=''.join('<li><a rel="noopener noreferrer" href="'+e(x['url'])+'">'+e(x['kind'].replace('_',' ').title())+'</a></li>' for x in d['links'])
  body='<a href="index.html">← Vegas venues</a><h1>'+e(d['name'])+'</h1><p>'+e(d['description'] or '')+'</p><dl>'+facts+'</dl><h2>Explore</h2><ul>'+links+'</ul><p>Source: <a href="'+e(d['source']['url'])+'">No Cover Nightclubs</a>. Observed '+e(d['source']['observed_at'])+'. Hours and policies can change; verify with the venue.</p><a href="../data/venues/'+e(slug)+'.json">JSON record</a>'
  (target/(slug+'.html')).write_text(page(d['name'],body))
  cards.append('<a class="card" href="'+e(slug)+'.html"><div><h2>'+e(d['name'])+'</h2><p>'+e(d['facts'].get('location',''))+'</p></div></a>')
 body='<a href="../index.html">DJ catalog</a><h1>Vegas, venue by venue.</h1><p>Nightlife and daytime destinations. Source-attributed venue facts.</p><label for="search">Find a venue</label><input id="search" type="search"><section class="grid">'+''.join(cards)+'</section><script>document.querySelector("#search").addEventListener("input",e=>document.querySelectorAll(".card").forEach(c=>c.hidden=!c.textContent.toLowerCase().includes(e.target.value.toLowerCase())))</script>'
 (target/'index.html').write_text(page('Vegas venues',body))
 dest=out/'data/venues';shutil.copytree(root/'data/venues',dest,dirs_exist_ok=True)
 (dest/'index.json').write_text(json.dumps({'venues':index},indent=2)+'\n')
 return len(rows)
if __name__=='__main__':print('Built',build(),'venue pages')
