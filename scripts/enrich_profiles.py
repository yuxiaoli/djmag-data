"""Sequential profile metadata enrichment with robots gating and checkpoints."""
from datetime import datetime,timezone
import argparse,json,time
from urllib.error import URLError
import socket
from pathlib import Path
from urllib.robotparser import RobotFileParser
from jsonschema import Draft202012Validator,FormatChecker
from sync import BASE,AGENT,fetch
from profile import parse_profile
from presentation import description
ROOT=Path(__file__).resolve().parents[1]
def main():
 a=argparse.ArgumentParser();a.add_argument('--max-profiles',type=int,default=1000);args=a.parse_args()
 if not 1<=args.max_profiles<=1000:raise ValueError('profile budget must be 1..1000')
 robots=RobotFileParser();robots.parse(fetch(BASE+'/robots.txt').splitlines())
 delay=max(10,robots.crawl_delay(AGENT) or 0)
 validator=Draft202012Validator(json.loads((ROOT/'data/dj.schema.json').read_text()),format_checker=FormatChecker())
 paths=sorted((ROOT/'data/djs').glob('*.json'), key=lambda p:(('profile_metadata' in json.loads(p.read_text())),json.loads(p.read_text())['updated_at'],p.name))[:args.max_profiles]
 for path in paths:
  d=json.loads(path.read_text());url=d['rankings'][-1]['source_url']
  if not robots.can_fetch(AGENT,url):raise RuntimeError('robots denied '+url)
  time.sleep(delay)
  try:
   raw=fetch(url)
  except URLError as exc:
   if not isinstance(exc.reason,(TimeoutError,socket.timeout)):raise
   print(f"timeout {d['id']}; preserved checkpoint; no immediate retry",flush=True)
   continue
  metadata=parse_profile(raw);now=datetime.now(timezone.utc).isoformat()
  if not metadata['intro_fields'] or metadata['article']['url'] != url:raise ValueError('Unexpected profile structure; stop without guessing')
  fields={x['label'].casefold():x['value'] for x in metadata['intro_fields']}
  d['profile_metadata']=metadata;d['origin']=fields.get('from');d['best_known_for']=fields.get('best known for');d['styles']=[fields['dj style']] if fields.get('dj style') else []
  # Compose an original summary only from explicit source facts; preserve raw movement.
  r=d['rankings'][-1];d['description']=description(d)
  if metadata['image_url']:d['image']['url']=metadata['image_url']
  r['previous_rank']=None # Source movement is retained verbatim, not inferred history.
  d['sources'].append(dict(url=url,publisher='DJ Mag',retrieved_at=now,fields=['/profile_metadata','/origin','/best_known_for','/styles','/description','/image','/rankings']))
  d['updated_at']=now;validator.validate(d)
  temp=path.with_suffix('.tmp');temp.write_text(json.dumps(d,indent=2,ensure_ascii=False)+'\n');temp.replace(path)
  print(f"enriched {d['id']}",flush=True)
if __name__=='__main__':main()
