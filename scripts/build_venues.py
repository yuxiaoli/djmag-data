"""Build a visual venue catalog without modifying DJ pages or source records."""
import html,json,re,shutil
from pathlib import Path
from urllib.parse import urlparse
ROOT=Path(__file__).resolve().parents[1]
def e(value):return html.escape(str(value),quote=True)
def safe_url(value):
 p=urlparse(value)
 return value if p.scheme in ('https','http') and p.hostname else None
def youtube_embed(value):
 p=urlparse(value)
 if p.scheme=='https' and p.hostname in ('www.youtube.com','youtube.com') and re.fullmatch(r'/embed/[A-Za-z0-9_-]{11}',p.path):return value
 return None
def photo(url,name,hero=False):
 cls='photo'+(' hero-photo' if hero else '')
 if not url:return '<div class="'+cls+' empty" role="img" aria-label="Venue image unavailable"></div>'
 return '<div class="'+cls+'"><img '+('' if hero else 'loading="lazy" ')+'src="'+e(url)+'" alt="'+e(name)+'" referrerpolicy="no-referrer" onerror="this.parentElement.classList.add(\'failed\')"></div>'
def page(title,body):
 return '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+e(title)+'</title><link rel="stylesheet" href="style.css"></head><body><main>'+body+'</main></body></html>'
def link_label(link):
 path=urlparse(link['url']).path.lower()
 if link['kind']=='virtual_tour':return 'Virtual tour'
 if link['kind']=='map':return 'Map & directions'
 if 'guest-list' in path:return 'Guest list'
 if 'table-service' in path:return 'Tables & reservations'
 if 'calendar' in path:return 'Event calendar'
 return 'More venue information'
def build(root=ROOT):
 out=root/'site';target=out/'venues';target.mkdir(parents=True,exist_ok=True)
 shutil.copyfile(root/'assets/venues.css',target/'style.css')
 rows=[json.loads(p.read_text()) for p in sorted((root/'data/venues').glob('*.json')) if p.name!='index.json'];cards=[];index=[]
 for d in rows:
  slug=d['id'];name=d['name'];links=[x for x in d['links'] if safe_url(x['url'])]
  images=list(dict.fromkeys(x['url'] for x in links if x['kind']=='image'));videos=[x['url'] for x in links if x['kind']=='video'];hero=images[0] if images else None
  index.append({'id':slug,'name':name,'type':d['listing_category'],'detail_url':'venues/'+slug+'.html','json_url':'data/venues/'+slug+'.json'})
  facts=''.join('<dt>'+e(k.replace('_',' ').title())+'</dt><dd>'+e(v)+'</dd>' for k,v in d['facts'].items())
  directory=''.join('<dt>'+e(k.title())+'</dt><dd>'+e(v)+'</dd>' for k,v in d.get('directory_facts',{}).items())
  media=''
  for n,url in enumerate(videos,1):
   embed=youtube_embed(url)
   media+=('<div class="video"><iframe loading="lazy" src="'+e(embed)+'" title="'+e(name)+' video '+str(n)+'" allow="fullscreen; picture-in-picture" allowfullscreen referrerpolicy="strict-origin-when-cross-origin"></iframe></div>' if embed else '')+'<p class="caption"><a href="'+e(url)+'" rel="noopener noreferrer">Watch original video'+(' '+str(n) if len(videos)>1 else '')+' at source</a> · If the player is unavailable, open the original video.</p>'
  gallery=''.join('<a href="'+e(url)+'" aria-label="Open '+e(name)+' photo">'+photo(url,name)+'</a>' for url in images[1:])
  if gallery:media+='<h2>More views</h2><div class="gallery">'+gallery+'</div>'
  actions=[];seen=set()
  for x in links:
   if x['kind'] in ('image','video'):continue
   label=link_label(x)
   key=(label,urlparse(x['url']).netloc,urlparse(x['url']).path.rstrip('/'))
   if key in seen:continue
   seen.add(key);actions.append('<a class="action" href="'+e(x['url'])+'" rel="noopener noreferrer">'+e(label)+'</a>')
  intro='<nav><a href="index.html">← Vegas venues</a><a href="../index.html">DJ catalog</a></nav><span class="eyebrow">'+e(d['listing_category'])+' · Las Vegas</span><h1>'+e(name)+'</h1><p class="lead">'+e(d['description'] or '')+'</p>'+photo(hero,name,True)
  if hero:intro+='<p class="caption"><a href="'+e(hero)+'">Open original photo</a> · Photo via No Cover Nightclubs.</p>'
  main='<div class="content-layout"><section>'+('<h2>Step inside</h2>'+media if media else '<h2>Explore the venue</h2><p class="lead">Visit the source for more photos and current venue information.</p>')+'<div class="actions">'+''.join(actions)+'</div></section><aside class="panel"><h2>At a glance</h2><dl>'+facts+'</dl>'+('<details><summary>Compare directory listing</summary><dl>'+directory+'</dl><p class="note">The directory and detail page may differ. Confirm current hours with the venue.</p></details>' if directory else '')+'</aside></div>'
  footer='<footer>Source: <a href="'+e(d['source']['url'])+'">No Cover Nightclubs</a> · Observed '+e(d['source']['observed_at'])+'<p>Hours and policies can change. Media belongs to its respective owners.</p><a href="../data/venues/'+e(slug)+'.json">JSON record</a></footer>'
  (target/(slug+'.html')).write_text(page(name,intro+main+footer))
  cards.append('<a class="card" href="'+e(slug)+'.html">'+photo(hero,name)+'<div class="card-content"><span class="badge">'+e(d['listing_category'])+'</span><h3>'+e(name)+'</h3><p>'+e(d['facts'].get('location',''))+'</p></div></a>')
 body='<nav><a href="../index.html">DJ catalog</a></nav><span class="eyebrow">The Las Vegas collection</span><h1>Find your next<br>scene.</h1><p class="lead">From poolside afternoons to late-night dance floors. Explore '+str(len(rows))+' Vegas venues, with a closer look inside.</p><div class="searchbox"><label for="search">Find a venue or hotel</label><input id="search" placeholder="Try Omnia, Encore or dayclub" type="search"></div><p id="empty" hidden>No venues match. Try another name or hotel.</p><section class="grid">'+''.join(cards)+'</section><footer>Venue information and media via <a href="https://nocovernightclubs.com/nightclubs/">No Cover Nightclubs</a>. Verify current hours and entry policies with the venue.</footer><script>document.querySelector("#search").addEventListener("input",e=>{let shown=0;document.querySelectorAll(".card").forEach(c=>{c.hidden=!c.textContent.toLowerCase().includes(e.target.value.toLowerCase());if(!c.hidden)shown++});document.querySelector("#empty").hidden=shown!==0})</script>'
 (target/'index.html').write_text(page('Vegas venues',body));dest=out/'data/venues';shutil.copytree(root/'data/venues',dest,dirs_exist_ok=True);(dest/'index.json').write_text(json.dumps({'venues':index},indent=2)+'\n');return len(rows)
if __name__=='__main__':print('Built',build(),'venue pages')
