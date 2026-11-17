"""Sequential profile metadata enrichment with robots gating and checkpoints."""
from datetime import datetime,timezone
import argparse,json,time
from urllib.error import URLError
import socket
from pathlib import Path
from urllib.robotparser import RobotFileParser
from jsonschema import Draft202012Validator,FormatChecker
from sync import BASE,AGENT,fetch,previous_rank_is_sourced
from profile import parse_profile
ROOT=Path(__file__).resolve().parents[1]
def main():
 a=argparse.ArgumentParser();a.add_argument('--max-profiles',type=int,default=1000);args=a.parse_args()
 if not 1<=args.max_profiles<=1000:raise ValueError('profile budget must be 1..1000')
 validator=Draft202012Validator(json.loads((ROOT/'data/dj.schema.json').read_text()),format_checker=FormatChecker())
 records=[]
 for path in (ROOT/'data/djs').glob('*.json'):
  d=json.loads(path.read_text());validator.validate(d)
  if not d['rankings']:raise ValueError(f'No ranking edition for {d["id"]}; collection incomplete')
  records.append((path,d,max(d['rankings'],key=lambda r:r['year'])))
 latest=max((r['year'] for _,_,r in records),default=None)
 records=sorted((item for item in records if item[2]['year']==latest),key=lambda item:(bool(item[1].get('profile_metadata')),item[1]['updated_at'],item[0].name))
 total = len(records)
 if not total:raise RuntimeError('No current-edition profiles; collection incomplete')
 robots=RobotFileParser();robots.parse(fetch(BASE+'/robots.txt').splitlines())
 delay=max(10,robots.crawl_delay(AGENT) or 0)
 completed = 0
 fresh_descriptions = 0
 missing_prior_descriptions = []
 for path,d,r in records[:args.max_profiles]:
  url=r['source_url']
  if not robots.can_fetch(AGENT,url):raise RuntimeError('robots denied '+url)
  time.sleep(delay)
  try:
   raw=fetch(url)
  except URLError as exc:
   if not isinstance(exc.reason,(TimeoutError,socket.timeout)):raise
   print(f"timeout {d['id']}; preserved checkpoint; no immediate retry",flush=True)
   continue
  metadata=parse_profile(raw);description=metadata.pop('description',None);now=datetime.now(timezone.utc).isoformat()
  if not metadata['intro_fields'] or metadata['article']['url'] != url:raise ValueError('Unexpected profile structure; stop without guessing')
  previous_facts={field:d.get(field) for field in ('profile_metadata','origin','best_known_for','styles','description')}
  fields={x['label'].casefold():x['value'] for x in metadata['intro_fields']}
  d['profile_metadata']=metadata;d['origin']=fields.get('from');d['best_known_for']=fields.get('best known for');d['styles']=[fields['dj style']] if fields.get('dj style') else []
  # Retain explicit source facts and movement without inventing biography text.
  source_fields=['/profile_metadata','/origin','/best_known_for','/styles']
  if description is not None:
   d['description']=description
   fresh_descriptions += 1
   source_fields.append('/description')
  elif d.get('description'):
   missing_prior_descriptions.append(d['id']) # Preserve old text and its original provenance; fail acceptance.
  # Without a recognized body, do not claim a newly observed null or redate retained text.
  if metadata['image_url']:
   if d['image'] is None or d['image']['url']!=metadata['image_url']:
    for source in d['sources']:source['fields']=[field for field in source['fields'] if field!='/image' and not field.startswith('/image/')]
    d['image']=dict(url=metadata['image_url'],source_url=url,credit=None,license=None,license_url=None)
   else:d['image']['url']=metadata['image_url'];d['image']['source_url']=url
   source_fields.append('/image')
  if not previous_rank_is_sourced(d,r):r['previous_rank']=None
  changed_fields={field for field,value in previous_facts.items() if value!=d.get(field)}
  for source in d['sources']:source['fields']=[field for field in source['fields'] if field.split('/')[1] not in changed_fields]
  d['sources'].append(dict(url=url,publisher='DJ Mag',retrieved_at=now,fields=source_fields))
  d['updated_at']=now;validator.validate(d)
  temp=path.with_suffix('.tmp');temp.write_text(json.dumps(d,indent=2,ensure_ascii=False)+'\n');temp.replace(path)
  completed += 1
  print(f"enriched {d['id']}; description_chars={len(description or '')}; description_status={'fetched' if description is not None else 'unavailable_or_unrecognized'}",flush=True)
 print(f'Description coverage: freshly extracted {fresh_descriptions}/{total}; missing bodies are unavailable or unrecognized',flush=True)
 if missing_prior_descriptions:raise RuntimeError('Description extraction incomplete; prior descriptions preserved for: '+', '.join(missing_prior_descriptions))
 if completed != total:raise RuntimeError(f'Profile collection incomplete: validated {completed}/{total} selected profiles; checkpoints preserved')
 print(f'Validated {completed}/{total} current-edition profiles for {latest}; unavailable factual fields remain unknown',flush=True)
if __name__=='__main__':main()
