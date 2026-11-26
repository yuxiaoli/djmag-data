"""Build a static catalog with stable artist URLs and public JSON."""
import html
import json
import shutil
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker, ValidationError

from presentation import movement

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
OUT = ROOT / 'site'
SITE_LANGUAGES = (
    ('en', 'English'),
    ('zh-CN', '简体中文'),
)


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def validate_previews(english):
    previews = [(filename, record) for filename, record in english.items() if 'preview_audio' in record]
    if not previews:
        return
    schema = read_json(DATA / 'dj.schema.json')
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    for filename, record in previews:
        try:
            validator.validate(record)
        except ValidationError as error:
            raise ValueError(f'{filename}: invalid preview record: {error.message}') from error
        if Path(filename).stem != record['id']:
            raise ValueError(f'{filename}: preview artist ID must match the filename')
        preview = record['preview_audio']
        cited = {source['url'] for source in record['sources'] if '/preview_audio' in source['fields']}
        if not {preview['source_url'], preview['rights_evidence_url']} <= cited:
            raise ValueError(f'{filename}: missing preview release or rights source')


def read_localized_profiles(english):
    paths = sorted((DATA / 'djs' / 'zh-CN').glob('*.json'))
    if not paths:
        return {}

    schema = read_json(DATA / 'dj.zh-CN.schema.json')
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    localized = {}
    for path in paths:
        record = read_json(path)
        try:
            validator.validate(record)
        except ValidationError as error:
            field = '/'.join(str(part) for part in error.absolute_path)
            raise ValueError(f'{path.name}: invalid localized profile at /{field}: {error.message}') from error
        if record['id'] != path.stem or english.get(path.name, {}).get('id') != record['id']:
            raise ValueError(f'{path.name}: localized ID and filename must match the English profile')

        fields = {'/name': record['name'], '/description': record['description'], '/aliases': record['aliases']}
        for index, alias in enumerate(record['aliases']):
            prefix = f'/aliases/{index}'
            fields[prefix] = alias
            fields.update({f'{prefix}/{key}': value for key, value in alias.items()})
        sourced = set()
        for source in record['sources']:
            for pointer in source['fields']:
                if not fields.get(pointer):
                    raise ValueError(f'{path.name}: source field {pointer} has no localized value')
                sourced.add(pointer)

        required_sources = {pointer for pointer in ('/name', '/description') if fields[pointer]}
        if '/aliases' not in sourced:
            for index in range(len(record['aliases'])):
                pointer = f'/aliases/{index}'
                if f'{pointer}/name' not in sourced:
                    required_sources.add(pointer)
        missing_sources = required_sources - sourced
        if missing_sources:
            detail = ', '.join(sorted(missing_sources))
            raise ValueError(f'{path.name}: missing localized sources for {detail}')
        localized[record['id']] = record
    return localized


def e(value):
    return html.escape(str(value))


def chinese_attribute(chinese):
    return f' data-zh="{e(chinese)}"' if chinese else ''


def localized_text(tag, english, chinese=None, attributes=''):
    return f'<{tag}{attributes}{chinese_attribute(chinese)}>{e(english)}</{tag}>'


def page(title, chinese_title, body, prefix='./', *, hide_language_label=False):
    language_options = ''.join(
        f'<option value="{e(code)}" lang="{e(code)}">{e(label)}</option>'
        for code, label in SITE_LANGUAGES
    )
    label_attributes = ' for="site-language"'
    if hide_language_label:
        label_attributes += ' class="visually-hidden"'
    return (
        f'<!doctype html><html lang="{e(SITE_LANGUAGES[0][0])}"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        + localized_text('title', title, chinese_title)
        + f'<link rel="stylesheet" href="{prefix}style.css">'
        + f'<script src="{prefix}dj-site.js" defer></script></head><body><main>'
        '<div class="language-switch">'
        + localized_text('label', 'Language', '语言', label_attributes)
        + f'<select id="site-language">{language_options}</select></div>'
        + body
        + '<footer><span data-zh="制作">Built by</span> '
        '<a href="https://s.vectorindex.cloud/sean">Sean</a> <span data-zh="❤️">with ❤️</span>'
        '</footer></main></body></html>'
    )


def artist_name(tag, english, chinese):
    return localized_text(tag, english, chinese, '' if chinese else ' lang="en"')


def artist_photo(artist, chinese_name):
    if not artist['image']:
        return ''
    chinese_alt = f' data-zh-alt="{e(chinese_name)}"' if chinese_name else ''
    return (
        '<img loading="lazy" referrerpolicy="no-referrer"'
        f' src="{e(artist["image"]["url"])}" alt="{e(artist["name"])}"{chinese_alt}>'
    )


def artist_card(artist, translation):
    rank = artist['rankings'][-1]
    chinese_name = translation.get('name')
    search_names = [artist['name'], chinese_name, *(alias['name'] for alias in translation.get('aliases', []))]
    search_index = json.dumps(list(dict.fromkeys(name for name in search_names if name)), ensure_ascii=False)
    return (
        f'<a class="card" href="djs/{e(artist["id"])}.html" data-dj-link data-search="{e(search_index)}">'
        + artist_photo(artist, chinese_name)
        + f'<div><span class="rank">{rank["rank"]}</span>'
        + artist_name('h2', artist['name'], chinese_name)
        + f'<small>DJ Mag {rank["year"]}</small></div></a>'
    )


def biography(english, chinese):
    def paragraphs(text):
        return ''.join(f'<p>{e(part)}</p>' for part in (text or '').split('\n\n') if part)

    if not chinese:
        return f'<div lang="en">{paragraphs(english)}</div>' if english else ''
    return (
        f'<div lang="en" data-bio-language="en">{paragraphs(english)}</div>'
        f'<div lang="zh-CN" data-bio-language="zh-CN" hidden>{paragraphs(chinese)}</div>'
    )


def aliases_markup(aliases):
    if not aliases:
        return ''
    names = ''.join(f'<li lang="{e(alias["language"])}">{e(alias["name"])}</li>' for alias in aliases)
    return localized_text('dt', 'Aliases', '别名') + f'<dd><ul class="alias-list" role="list">{names}</ul></dd>'


def preview_markup(preview):
    if not preview:
        return ''
    provider = preview['provider']
    height = {'Apple Podcasts': 175, 'Apple Music': 220, 'Spotify': 152, 'SoundCloud': 320, 'Beatport': 162}[provider]
    return (
        '<section class="audio-preview">'
        + localized_text('h2', 'Listen', '试听')
        + f'<iframe title="{e(preview["title"])} · {e(provider)}" src="{e(preview["embed_url"])}"'
        + f' height="{height}" loading="lazy" allow="encrypted-media"'
        + ' referrerpolicy="strict-origin-when-cross-origin"></iframe></section>'
    )


def chinese_movement(artist):
    metadata = artist.get('profile_metadata') or {}
    direction = metadata.get('movement')
    translation = {
        None: '来源未显示',
        'Up': '上升',
        'Down': '下降',
        'New entry': '首次上榜',
        'Non-mover': '排名不变',
        'Re-entry': '重新上榜',
    }.get(direction)
    places = metadata.get('movement_places')
    return f'{translation} · {places} 位' if translation and places is not None else translation


def artist_page(artist, translation):
    rank = artist['rankings'][-1]
    chinese_name = translation.get('name')
    primary_facts = (
        ('From', '来自', artist.get('origin'), None),
        ('DJ style', 'DJ 风格', ', '.join(artist['styles']), None),
        ('Best known for', '代表成就', artist.get('best_known_for'), None),
        ('Ranking change', '排名变化', movement(artist), chinese_movement(artist)),
    )
    details = ''.join(
        localized_text('dt', label, chinese_label)
        + localized_text('dd', value or '', chinese_value, ' lang="en"' if value and not chinese_value else '')
        for label, chinese_label, value, chinese_value in primary_facts
    )
    secondary = aliases_markup(translation.get('aliases', []))
    birth_date = artist.get('birth_date')
    if birth_date:
        secondary += (
            localized_text('dt', 'Birth date', '出生日期') + f'<dd>{e(birth_date)}</dd>'
            + localized_text('dt', 'Age', '年龄', ' hidden')
            + f'<dd hidden data-birth-date="{e(birth_date)}"></dd>'
        )
    for field in (artist.get('profile_metadata') or {}).get('intro_fields', []):
        if field['label'].casefold() not in ('from', 'dj style', 'best known for', 'birth date', 'age', 'gender'):
            secondary += f'<dt lang="en">{e(field["label"])}</dt><dd lang="en">{e(field["value"])}</dd>'

    body = (
        localized_text('a', '← All DJs', '← 返回榜单', ' href="../index.html" data-dj-link')
        + f'<p class="eyebrow">DJ MAG TOP 100 · {rank["year"]}</p>'
        + artist_name('h1', artist['name'], chinese_name)
        + artist_photo(artist, chinese_name)
        + localized_text('p', 'Current Ranking', '本期排名', ' class="ranking-label"')
        + f'<p class="big">#{rank["rank"]}</p><dl class="profile-facts">{details}</dl>'
        + preview_markup(artist.get('preview_audio'))
        + '<section class="profile-details">'
        + localized_text('h2', 'Profile details', 'DJ 档案')
        + biography(artist.get('description'), translation.get('description'))
        + f'<dl>{secondary}</dl></section>'
        + localized_text('p', f'Updated {artist["updated_at"]}', f'更新于 {artist["updated_at"]}')
        + localized_text('a', 'JSON record', '英文 JSON 档案', f' href="../data/djs/en/{e(artist["id"])}.json"')
        + localized_text(
            'p', 'Photos are linked from the source; rights remain with their owners. Unknown facts are not inferred.',
            '照片链接来自原始来源，版权归权利人所有。档案仅记录有据可查的资料。', ' class="note"'
        )
    )
    if birth_date:
        body += '<script src="../dj-age.js" defer></script>'
    return page(artist['name'], chinese_name, body, '../', hide_language_label=True)


def ranking_page(rows, localized, year):
    cards = ''.join(artist_card(artist, localized.get(artist['id'], {})) for artist in rows)
    edition = str(year) if year else 'Unknown'
    chinese_edition = f'{year} 年' if year else '年份未知'
    body = (
        localized_text('p', 'INDEPENDENT DATA CATALOG', '独立资料库', ' class="eyebrow"')
        + localized_text('h1', 'The people\nbehind the decks.', 'DJ Mag 百大 DJ 榜单', ' class="ranking-title"')
        + localized_text('p', f'DJ Mag latest rankings · {edition} · {len(rows)} artists',
                         f'DJ Mag 最新榜单 · {chinese_edition} · {len(rows)} 位艺人')
        + localized_text('label', 'Find a DJ', '搜索 DJ', ' for="search"')
        + '<input id="search" placeholder="Search artists…" data-zh-placeholder="搜索艺名或别名…" type="search">'
        + f'<section class="grid">{cards}</section>'
        + localized_text('p', 'No matching DJs.', '未找到符合条件的 DJ。', ' role="status" data-no-results hidden')
    )
    return page('DJ catalog', 'DJ Mag 百大 DJ 榜单', body, hide_language_label=True)


english = {path.name: read_json(path) for path in (DATA / 'djs' / 'en').glob('*.json')}
validate_previews(english)
localized = read_localized_profiles(english)
OUT.mkdir(exist_ok=True)
latest = max((record['rankings'][-1]['year'] for record in english.values()), default=0)
rows = sorted(
    (record for record in english.values() if record['rankings'][-1]['year'] == latest),
    key=lambda record: record['rankings'][-1]['rank'],
)
(OUT / 'djs').mkdir(exist_ok=True)
for artist in rows:
    artist_id = artist['id']
    (OUT / 'djs' / f'{artist_id}.html').write_text(
        artist_page(artist, localized.get(artist_id, {})), encoding='utf-8'
    )
(OUT / 'index.html').write_text(ranking_page(rows, localized, latest), encoding='utf-8')
for asset in ('dj-age.js', 'dj-site.js'):
    shutil.copyfile(ROOT / 'assets' / asset, OUT / asset)
shutil.copytree(DATA,OUT/'data',dirs_exist_ok=True,ignore=shutil.ignore_patterns('.gitkeep','djmag-research.*.output.*.json'))
# Publish the historical record URLs as byte-identical build artifacts.
for source in (DATA/'djs/en').glob('*.json'):
 shutil.copyfile(source,OUT/'data'/'djs'/source.name)
(OUT/'style.css').write_text('''*{box-sizing:border-box}body{margin:0;background:#0c1016;color:#eef1f7;font:16px/1.55 system-ui,sans-serif}main{max-width:1180px;margin:auto;padding:50px 24px}a{color:#acbfff}h1{font-size:clamp(40px,7vw,82px);line-height:1.05;letter-spacing:-.05em;margin:20px 0}h2{font-size:20px;margin:0}.eyebrow{letter-spacing:.18em;color:#a8b7d7;font-size:12px}input{display:block;width:100%;background:#161e2b;border:1px solid #38445a;color:white;padding:16px;border-radius:10px;margin:10px 0 28px;font:inherit}.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:18px}.card{display:block;text-decoration:none;background:#171e2a;border:1px solid #273044;border-radius:12px;overflow:hidden;color:inherit}.card[hidden]{display:none}.card div{padding:16px}.card:hover{border-color:#9caeff}img{max-width:100%;border-radius:8px}.card img{width:100%;aspect-ratio:323/182;object-fit:cover;border-radius:0}.rank{float:right;font-size:28px;color:#a7b8fb}small,.note,footer{color:#9eabc1}.note{max-width:720px}.ranking-label,.profile-facts dt,.profile-details dt,.profile-details h2{color:#9eabc1;font-size:16px;font-weight:400;line-height:1.55;letter-spacing:normal;margin:12px 0 0}.big{font-size:16px;font-weight:400;line-height:1.55;margin:0}dt{color:#9eabc1;margin-top:12px}dd{margin:0}footer{margin-top:60px;font-size:13px}.profile-facts{margin:12px 0 24px}.profile-details{max-width:800px;margin:0 0 36px;overflow-wrap:anywhere}.profile-details p{margin:0 0 18px}.ranking-title{white-space:pre-line}.language-switch{display:flex;align-items:center;justify-content:flex-end;gap:8px;margin-bottom:16px}.language-switch label{color:#9eabc1}.visually-hidden{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip-path:inset(50%);white-space:nowrap;border:0}.alias-list{list-style:none;text-align:left;margin:0;padding:0}.audio-preview{max-width:640px;margin:20px 0 28px}.audio-preview h2{margin-bottom:8px}.audio-preview iframe{display:block;width:100%;border:0;border-radius:8px}@media(max-width:360px){main{padding-inline:14px}}.language-switch select{font:inherit;color:inherit;color-scheme:dark;background:#171e2a;border:1px solid #38445a;border-radius:8px;padding:5px 10px}''',encoding='utf-8')
(OUT/'data'/'index.json').write_text(json.dumps({'ranking_year':latest,'artists':[{'id':d['id'],'name':d['name'],'rank':d['rankings'][-1]['rank'],'record_url':'data/djs/en/'+d['id']+'.json','detail_url':'djs/'+d['id']+'.html'} for d in rows]},indent=2)+'\n',encoding='utf-8')
print(f'Built {len(rows)} detail pages')
