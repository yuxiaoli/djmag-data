"""Independent annual venue collector; robots-aware, bounded, atomic records, no retries."""
import datetime,html,json,re,time,urllib.request,urllib.robotparser
from pathlib import Path
from urllib.parse import urlparse
from venue import extract,listing_facts
ROOT=Path(__file__).resolve().parents[1];BASE='https://nocovernightclubs.com';AGENT='VenueCatalogBot/1.0'
def fetch(url):
 if urlparse(url).scheme != 'https' or urlparse(url).hostname != 'nocovernightclubs.com':raise ValueError('Unexpected source URL')
 with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':AGENT}),timeout=35) as r:
  if r.url.split('/')[2]!='nocovernightclubs.com':raise ValueError('Unexpected redirect host')
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
 rp=urllib.robotparser.RobotFileParser();rp.parse(fetch(BASE+'/robots.txt').splitlines())
 delay=crawl_delay(rp)
 rows=[]
 for path,typ in [('/nightclubs/','nightclub'),('/pool-parties/','dayclub')]:
  url=BASE+path
  if not rp.can_fetch(AGENT,url):raise RuntimeError('Robots denies directory')
  time.sleep(delay);markup=fetch(url);urls=discover(markup)
  if not urls or len(urls)>100:raise ValueError('Unexpected directory coverage')
  rows.extend((u,typ,url,listing_facts(markup,u)) for u in urls)
 records=[]
 for url,typ,listing,directory in rows:
  if not rp.can_fetch(AGENT,url):raise RuntimeError('Robots denies venue')
  time.sleep(delay);markup=fetch(url);record=extract(markup,url,typ,datetime.datetime.now(datetime.timezone.utc).isoformat())
  record['source']['listing_url']=listing;record['directory_facts']=directory;records.append(record)
 # Fail closed: no public record mutation unless every discovered page parsed.
 import jsonschema
 schema=json.loads((ROOT/'data/venue.schema.json').read_text())
 for r in records:jsonschema.validate(r,schema,format_checker=jsonschema.FormatChecker())
 dest=ROOT/'data/venues';dest.mkdir(exist_ok=True)
 for r in records:
  path=dest/(r['id']+'.json');temp=path.with_suffix('.tmp');temp.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n');temp.replace(path)
 print('Validated',len(records),'venue records')
if __name__=='__main__':run()
