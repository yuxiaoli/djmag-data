"""Conservative DJ Mag ranking metadata importer; never copies editorial text."""
import argparse
from datetime import datetime, timezone
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import time
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen
from urllib.robotparser import RobotFileParser

BASE = 'https://djmag.com'
AGENT = 'SeanDJCatalog/1.0 (+https://github.com/yuxiaoli/djmag-data)'

class RankingParser(HTMLParser):
    def __init__(self):
        super().__init__(); self.rows = {}; self.images = {}; self.current = None; self.parts = []
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'img':
            rank = re.search(r'Position (\d+)', a.get('alt',''))
            if rank and a.get('src'): self.images[int(rank.group(1))] = urljoin(BASE,a['src'])
        if tag == 'a':
            m = re.fullmatch(r'/top100djs/(\d{4})/(\d{1,6})/([a-z0-9-]+)/?', a.get('href',''))
            if m:
                self.current = tuple(m.groups()); self.parts = []
    def handle_data(self, data):
        if self.current: self.parts.append(data)
    def handle_endtag(self, tag):
        if tag == 'a' and self.current:
            name = ' '.join(' '.join(self.parts).split())
            if name: self.rows[self.current] = name
            self.current = None

def parse_rankings(html, observed_at):
    p = RankingParser(); p.feed(html)
    if not p.rows: raise ValueError('No recognized ranking records; preserve previous snapshot')
    years = {int(key[0]) for key in p.rows}
    year = max(years)
    rows = [(k,n) for k,n in p.rows.items() if int(k[0]) == year]
    ranks = [int(k[1]) for k,n in rows]
    if len(rows) < 100 or set(ranks) != set(range(1,len(rows)+1)):
        raise ValueError('Expected unique contiguous current-edition ranks starting at 1 (at least 100); preserve previous snapshot')
    out = []
    for (y,r,slug),name in rows:
        url = f'{BASE}/top100djs/{y}/{r}/{slug}'
        out.append(dict(schema_version='1.0.0',id=slug,name=name,entity_type='unknown',description=None,nationalities=[],styles=[],birth_date=None,gender=None,image=None,rankings=[dict(year=int(y),rank=int(r),previous_rank=None,source_url=url)],sources=[dict(url=url,publisher='DJ Mag',retrieved_at=observed_at,fields=['/name','/rankings'])],updated_at=observed_at))
    for row in out:
        image_url = p.images.get(row['rankings'][0]['rank'])
        if image_url:
            row['image'] = dict(url=image_url,source_url=row['rankings'][0]['source_url'],credit=None,license=None,license_url=None)
            row['sources'][0]['fields'].append('/image')
    if len({x['id'] for x in out}) !=len(out): raise ValueError('Duplicate artist IDs')
    return out

def fetch(url):
    if urlparse(url).hostname != 'djmag.com': raise ValueError('Unexpected source host')
    with urlopen(Request(url, headers={'User-Agent':AGENT}), timeout=30) as response:
        if urlparse(response.url).hostname != 'djmag.com': raise ValueError('Unexpected redirect host')
        if response.status != 200: raise ValueError('Source unavailable')
        data=response.read(5_000_001)
        if len(data)>5_000_000: raise ValueError('Response too large')
        return data.decode('utf-8')

def previous_rank_is_sourced(record, ranking):
    index = record['rankings'].index(ranking)
    fields = {'/rankings', f'/rankings/{index}', f'/rankings/{index}/previous_rank'}
    return ranking['previous_rank'] is not None and any(
        source['url'] == ranking['source_url'] and fields.intersection(source['fields'])
        for source in record['sources'])


def relocated_ranking_field(old, row, field):
    parts = field.split('/')[2:]
    if not parts or not parts[0].isdigit():
        return None
    try:
        previous = old['rankings'][int(parts[0])]
        current_index = next(index for index, ranking in enumerate(row['rankings'])
            if all(previous[key] == ranking[key] for key in ('year', 'rank', 'source_url')))
        old_value, new_value = previous, row['rankings'][current_index]
        for part in parts[1:]:
            key = part.replace('~1', '/').replace('~0', '~')
            old_value, new_value = old_value[key], new_value[key]
        if old_value == new_value:
            return '/rankings/' + str(current_index) + ''.join('/' + part for part in parts[1:])
    except (IndexError, KeyError, StopIteration, TypeError):
        pass
    return None


def refresh_sources(old, row, retained_ranking_urls, preserved_image):
    """Retain unchanged field attribution and replace refreshed ranking claims."""
    retained = []
    for source in old['sources']:
        fields = []
        for field in source['fields']:
            if field == '/name' or field.startswith('/name/') or field == '/updated_at':
                continue
            if field == '/rankings':
                if source['url'] not in retained_ranking_urls:
                    continue
                fields.append(field)
                continue
            elif field.startswith('/rankings/'):
                relocated = relocated_ranking_field(old, row, field)
                if relocated:
                    fields.append(relocated)
                continue
            root_field = field.split('/')[1]
            if root_field not in row or old.get(root_field) != row[root_field]:
                continue
            fields.append(field)
        if fields:
            retained.append(dict(source, fields=fields))
    fresh = row['sources']
    if preserved_image:
        fresh = [dict(source, fields=[field for field in source['fields'] if field != '/image' and not field.startswith('/image/')]) for source in fresh]
    return retained + fresh


def main():
    a=argparse.ArgumentParser();a.add_argument('--fixture',type=Path);a.add_argument('--output',type=Path,default=Path('data/djs'));args=a.parse_args()
    if args.fixture: html=args.fixture.read_text()
    else:
        robots=RobotFileParser(); robots.parse(fetch(BASE+'/robots.txt').splitlines())
        url=BASE+'/top100djs'
        if not robots.can_fetch(AGENT,url): raise RuntimeError('robots.txt disallows this crawler; no collection performed')
        time.sleep(max(10,robots.crawl_delay(AGENT) or 0));html=fetch(url)
    now=datetime.now(timezone.utc).isoformat();rows=parse_rankings(html,now)
    from jsonschema import Draft202012Validator,FormatChecker
    schema=json.loads((Path(__file__).resolve().parents[1]/'data/dj.schema.json').read_text())
    validator=Draft202012Validator(schema,format_checker=FormatChecker())
    for row in rows: validator.validate(row)
    # Stage fully validated data; no deletes. Existing enrichment/history survives refresh.
    staged={}
    for row in rows:
        path=args.output/(row['id']+'.json')
        if path.exists():
            old=json.loads(path.read_text());validator.validate(old)
            preserved_image = old['image'] is not None
            for field in ('entity_type','description','nationalities','styles','birth_date','gender','image'):
                if old[field] is not None and old[field] != []: row[field]=old[field]
            for field in ('origin','best_known_for','profile_metadata'):
                if field in old: row[field]=old[field]
            historical_rankings=[r for r in old['rankings'] if r['year']!=row['rankings'][0]['year']]
            retained_ranking_urls={r['source_url'] for r in historical_rankings}
            refreshed_rank=row['rankings'][0]
            for previous in old['rankings']:
                unchanged=all(previous[key]==refreshed_rank[key] for key in ('year','rank','source_url'))
                sourced=previous_rank_is_sourced(old,previous)
                if unchanged and previous['previous_rank'] is not None and sourced:
                    refreshed_rank['previous_rank']=previous['previous_rank']
                    retained_ranking_urls.add(previous['source_url'])
            row['rankings']=sorted(historical_rankings+row['rankings'],key=lambda r:r['year'])
            row['sources']=refresh_sources(old,row,retained_ranking_urls,preserved_image)
        validator.validate(row);staged[path]=json.dumps(row,indent=2,ensure_ascii=False)+'\n'
    args.output.mkdir(parents=True,exist_ok=True)
    for path,body in staged.items():path.write_text(body)
    print(f'Validated {len(rows)} profiles; ranking year {rows[0]["rankings"][0]["year"]}; observed {now}')
if __name__=='__main__':main()
