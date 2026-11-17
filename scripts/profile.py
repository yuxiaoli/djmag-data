"""Extract explicitly labelled profile facts, excluding sitewide publisher socials."""
from html import unescape
from html.parser import HTMLParser
import json,re
class Text(HTMLParser):
 def __init__(self):super().__init__();self.parts=[]
 def handle_data(self,data):self.parts.append(data)
def plain(fragment):
 p=Text();p.feed(fragment);return ' '.join(' '.join(p.parts).split())
class Biography(HTMLParser):
 """Read only the explicit editorial body, never the surrounding site chrome."""
 void={'br','img','hr','input','meta','link','source','wbr','embed'}
 blocks={'p','div','section','h2','h3','h4','li','blockquote'}
 excluded={'script','style','nav','aside','figure','iframe','button','form'}
 def __init__(self):
  super().__init__();self.stack=[];self.depth=None;self.skip=None;self.parts=[];self.bodies=[]
 def handle_starttag(self,tag,attrs):
  a=dict(attrs);classes=set(a.get('class','').split())
  if self.depth is None and (classes & {'field--name-body','field--name-field-body'} or a.get('itemprop')=='articleBody'):
   self.depth=len(self.stack);self.parts=[]
  if self.depth is not None:
   if tag in self.excluded and self.skip is None:self.skip=len(self.stack)
   if self.skip is None and (tag in self.blocks or tag=='br'):self.parts.append('\n\n')
  if tag not in self.void:self.stack.append(tag)
 def handle_startendtag(self,tag,attrs):
  self.handle_starttag(tag,attrs)
  if tag not in self.void:self.handle_endtag(tag)
 def handle_endtag(self,tag):
  if tag not in self.stack:return
  index=len(self.stack)-1-self.stack[::-1].index(tag)
  if self.depth is not None and self.skip is None and tag in self.blocks:self.parts.append('\n\n')
  del self.stack[index:]
  if self.skip is not None and len(self.stack)<=self.skip:self.skip=None
  if self.depth is not None and len(self.stack)<=self.depth:
   text='\n\n'.join(' '.join(p.split()) for p in ''.join(self.parts).split('\n\n') if p.strip())
   if text and text not in self.bodies:self.bodies.append(text)
   self.depth=None
 def handle_data(self,data):
  if self.depth is not None and self.skip is None:self.parts.append(data)

def biography(html,article):
 parser=Biography();parser.feed(html);parser.close()
 if parser.bodies:return '\n\n'.join(parser.bodies)
 body=article.get('articleBody')
 if isinstance(body,str) and body.strip():
  # articleBody is the full text field; never substitute the short meta description.
  return '\n\n'.join(plain(p) for p in body.split('\n') if plain(p)) or None
 return None

def parse_profile(html):
 fields=[]
 for block in re.findall(r'<div[^>]*field--name-field-intro[^>]*>(.*?)</div>',html,re.S):
  for label,value in re.findall(r'<p[^>]*>\s*<strong>(.*?)</strong>(.*?)</p>',block,re.S):
   item={'label':plain(label).rstrip(': '),'value':plain(value)}
   if item not in fields:fields.append(item)
 movement=re.search(r'<span[^>]*entry-header__movement-text[^>]*>(.*?)</span>',html,re.S)
 places=re.search(r'<div[^>]*field--name-field-top-100-places[^>]*>(.*?)</div>',html,re.S)
 places=int(plain(places.group(1))) if places and plain(places.group(1)).isdigit() else None
 article={}
 for raw in re.findall(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>',html,re.S):
  data=json.loads(raw)
  for node in data.get('@graph',[data]):
   if node.get('@type')=='Article':article=node;break
 return {'description':biography(html,article),'intro_fields':fields,'movement_places':places,'movement':plain(movement.group(1)) if movement else None,'article':{'headline':article.get('headline'),'published_at':article.get('datePublished'),'modified_at':article.get('dateModified'),'author_name':(article.get('author') or {}).get('name'),'url':article.get('mainEntityOfPage')},'image_url':(article.get('image') or {}).get('url')}
