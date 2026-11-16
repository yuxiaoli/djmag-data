"""Independent annual venue collector; robots-aware, bounded, atomic records, no retries."""
import datetime,html,json,re,time,urllib.request,urllib.robotparser
from pathlib import Path
from urllib.parse import urlparse
from venue import extract,listing_facts
ROOT=Path(__file__).resolve().parents[1];BASE='https://nocovernightclubs.com';AGENT='VenueCatalogBot/1.0'
DIRECTORIES=[('/nightclubs/','nightclub'),('/pool-parties/','dayclub')]

def known_roster():
 expected={BASE+path:category for path,category in DIRECTORIES}
 roster=set()
 for path in (ROOT/'data/venues').glob('*.json'):
  record=json.loads(path.read_text())
  if not isinstance(record,dict) or not isinstance(record.get('source'),dict):continue
  source=record['source'];listing=source.get('listing_url');url=source.get('url')
  if not isinstance(listing,str) or listing not in expected or not isinstance(url,str) or urlparse(url).hostname!='nocovernightclubs.com':continue
  category=record.get('listing_category');identity=record.get('id')
  if category not in ('nightclub','dayclub'):continue
  if category!=expected[listing] or identity!=urlparse(url).path.strip('/').split('/')[-1] or identity!=path.stem:
   raise ValueError(f'Stored venue baseline identity mismatch: {path.name}; preserve previous snapshot')
  roster.add((identity,category,url,listing))
 return roster
def validate_source_url(url):
 parsed=urlparse(url)
 if parsed.scheme!='https' or parsed.hostname!='nocovernightclubs.com' or parsed.username is not None or parsed.password is not None or parsed.port not in (None,443):raise ValueError('Unexpected source URL')

class SourceRedirectHandler(urllib.request.HTTPRedirectHandler):
 def __init__(self,delay=10,robots=None):self.delay=max(10,float(delay));self.robots=robots
 def redirect_request(self,req,fp,code,msg,headers,newurl):
  validate_source_url(newurl)
  if self.robots is not None and not self.robots.can_fetch(AGENT,newurl):raise RuntimeError('Robots denies redirect '+newurl)
  time.sleep(self.delay)
  return super().redirect_request(req,fp,code,msg,headers,newurl)

def fetch(url,redirect_delay=10,robots=None):
 validate_source_url(url)
 if robots is not None and not robots.can_fetch(AGENT,url):raise RuntimeError('Robots denies source '+url)
 with urllib.request.build_opener(SourceRedirectHandler(redirect_delay,robots)).open(urllib.request.Request(url,headers={'User-Agent':AGENT}),timeout=35) as r:
  validate_source_url(r.url)
  raw=r.read(4000001)
  if len(raw)>4000000:raise ValueError('Page exceeds safety budget')
  return raw.decode('utf-8')
def discover(markup):
 return list(dict.fromkeys(html.unescape(h) for h,t in re.findall(r'<a[^>]+href=["\x27]([^"\x27]+)["\x27][^>]*>(.*?)</a>',markup,re.S) if re.sub('<[^>]+>','',t).strip()=='Club Details'))
def crawl_delay(rp):
 delay=rp.crawl_delay(AGENT) or rp.crawl_delay('*') or 0
 rate=rp.request_rate(AGENT) or rp.request_rate('*')
 return max(10,float(delay),rate.seconds/rate.requests if rate and rate.requests else 0)
def run():
 baseline=known_roster()
 rp=urllib.robotparser.RobotFileParser();rp.parse(fetch(BASE+'/robots.txt').splitlines())
 delay=crawl_delay(rp)
 rows=[]
 for path,typ in DIRECTORIES:
  url=BASE+path
  if not rp.can_fetch(AGENT,url):raise RuntimeError('Robots denies directory')
  time.sleep(delay);markup=fetch(url,redirect_delay=delay,robots=rp);urls=discover(markup)
  if not urls or len(urls)>100:raise ValueError('Unexpected directory coverage')
  rows.extend((u,typ,url,listing_facts(markup,u)) for u in urls)
 discovered={(urlparse(url).path.strip('/').split('/')[-1],typ,url,listing) for url,typ,listing,_ in rows}
 missing=sorted(baseline-discovered)
 if missing:raise ValueError('Venue directory coverage incomplete; missing '+ '; '.join(f'{identity} ({category}) {url} from {listing}' for identity,category,url,listing in missing))
 records=[]
 for url,typ,listing,directory in rows:
  if not rp.can_fetch(AGENT,url):raise RuntimeError('Robots denies venue')
  time.sleep(delay);markup=fetch(url,redirect_delay=delay,robots=rp);record=extract(markup,url,typ,datetime.datetime.now(datetime.timezone.utc).isoformat())
  if not any(record['facts'].get(field) for field in ('location','nights','days','music','size')):raise ValueError('Unexpected venue profile structure: '+url)
  record['source']['listing_url']=listing;record['directory_facts']=directory;records.append(record)
 # Fail closed: no public record mutation unless every discovered page parsed.
 if len({record['id'] for record in records})!=len(records):raise ValueError('Duplicate venue IDs; preserve previous snapshot')
 import jsonschema
 schema=json.loads((ROOT/'data/venue.schema.json').read_text())
 for r in records:jsonschema.validate(r,schema,format_checker=jsonschema.FormatChecker())
 dest=ROOT/'data/venues';dest.mkdir(exist_ok=True)
 for r in records:
  path=dest/(r['id']+'.json');temp=path.with_suffix('.tmp');temp.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n');temp.replace(path)
 print('Validated',len(records),'venue records')
if __name__=='__main__':run()
