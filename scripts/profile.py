"""Extract explicitly labelled profile facts, excluding sitewide publisher socials."""
from html import unescape
from html.parser import HTMLParser
import json,re
class Text(HTMLParser):
 def __init__(self):super().__init__();self.parts=[]
 def handle_data(self,data):self.parts.append(data)
def plain(fragment):
 p=Text();p.feed(fragment);return ' '.join(' '.join(p.parts).split())
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
 return {'intro_fields':fields,'movement_places':places,'movement':plain(movement.group(1)) if movement else None,'article':{'headline':article.get('headline'),'published_at':article.get('datePublished'),'modified_at':article.get('dateModified'),'author_name':(article.get('author') or {}).get('name'),'url':article.get('mainEntityOfPage')},'image_url':(article.get('image') or {}).get('url')}
