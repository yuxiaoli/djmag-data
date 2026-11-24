"""Build a visual venue catalog without modifying DJ pages or source records."""
import html
import json
import re
import shutil
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
FACT_LABELS_ZH = {
    'location': '所在地点',
    'nights': '夜间营业日',
    'days': '营业日',
    'music': '音乐风格',
    'size': '面积',
    'address': '地址',
    'hours': '营业时间',
}
CATEGORY_LABELS_ZH = {'dayclub': '日间俱乐部', 'nightclub': '夜店'}
SEARCH_SCRIPT = (
    '<script>document.querySelector("#search").addEventListener("input",e=>{'
    'let shown=0;document.querySelectorAll(".card").forEach(c=>{'
    'c.hidden=!c.textContent.toLowerCase().includes(e.target.value.toLowerCase());'
    'if(!c.hidden)shown++});document.querySelector("#empty").hidden=shown!==0})</script>'
)


def e(value):
    return html.escape(str(value), quote=True)


def safe_url(value):
    parsed = urlparse(value)
    return value if parsed.scheme in ('https', 'http') and parsed.hostname else None


def youtube_embed(value):
    parsed = urlparse(value)
    if (
        parsed.scheme == 'https'
        and parsed.hostname in ('www.youtube.com', 'youtube.com')
        and re.fullmatch(r'/embed/[A-Za-z0-9_-]{11}', parsed.path)
    ):
        return value
    return None


def photo(url, name, hero=False, chinese=False):
    classes = 'photo hero-photo' if hero else 'photo'
    if not url:
        label = '暂无场馆图片' if chinese else 'Venue image unavailable'
        return f'<div class="{classes} empty" role="img" aria-label="{label}"></div>'
    loading = '' if hero else 'loading="lazy" '
    return (
        f'<div class="{classes}"><img {loading}src="{e(url)}" alt="{e(name)}" '
        'referrerpolicy="no-referrer" onerror="this.parentElement.classList.add(\'failed\')"></div>'
    )


def page(title, body, chinese=False):
    language = 'zh-CN' if chinese else 'en'
    stylesheet = '../style.css' if chinese else 'style.css'
    return (
        f'<!doctype html><html lang="{language}"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<title>{e(title)}</title><link rel="stylesheet" href="{stylesheet}"></head>'
        f'<body><main>{body}</main></body></html>'
    )


def link_label(link, chinese=False):
    path = urlparse(link['url']).path.lower()
    if link['kind'] == 'virtual_tour':
        return '线上导览' if chinese else 'Virtual tour'
    if link['kind'] == 'map':
        return '地图与路线' if chinese else 'Map & directions'
    if 'guest-list' in path:
        return '宾客名单' if chinese else 'Guest list'
    if 'table-service' in path:
        return '卡座与预订' if chinese else 'Tables & reservations'
    if 'calendar' in path:
        return '活动日历' if chinese else 'Event calendar'
    return '更多场馆信息' if chinese else 'More venue information'


def navigation(chinese, alternate, detail=False):
    links = []
    if detail:
        venue_label = '← 拉斯维加斯场馆' if chinese else '← Vegas venues'
        links.append(f'<a href="index.html">{venue_label}</a>')
    if chinese:
        links.append('<a href="../../index.html?lang=zh-CN">DJ 榜单</a>')
    else:
        links.append('<a href="../index.html">DJ catalog</a>')
    if alternate:
        language, label = ('en', 'English') if chinese else ('zh-CN', '简体中文')
        links.append(f'<a href="{e(alternate)}" lang="{language}" hreflang="{language}">{label}</a>')
    return '<nav>' + ''.join(links) + '</nav>'


def branding(chinese):
    author = '<a href="https://s.vectorindex.cloud/sean">Sean</a>'
    return f'<p>由 {author} 制作 ❤️</p>' if chinese else f'<p>Built by {author} with ❤️</p>'


def fact_list(facts, chinese, directory=False):
    terms = []
    for key, value in facts.items():
        english = key.title() if directory else key.replace('_', ' ').title()
        label = FACT_LABELS_ZH.get(key, english) if chinese else english
        terms.append(f'<dt>{e(label)}</dt><dd>{e(value)}</dd>')
    return ''.join(terms)


def review_notes(quality, chinese):
    conflicts = quality.get('source_conflicts', [])
    if not conflicts:
        return ''
    heading = '来源核对说明' if chinese else 'Source review notes'
    date = quality.get('source_conflicts_observed_at')
    date_label = '核对所用资料的采集时间' if chinese else 'Review source observed'
    observed = f'<p>{date_label} {e(date)}</p>' if date else ''
    notes = ''.join(f'<li>{e(note)}</li>' for note in conflicts)
    return f'<section class="note"><h2>{heading}</h2>{observed}<ul>{notes}</ul></section>'


def venue_media(name, videos, gallery_images, chinese):
    media = []
    for number, url in enumerate(videos, 1):
        embed = youtube_embed(url)
        if embed:
            title = f'{name} 视频 {number}' if chinese else f'{name} video {number}'
            media.append(
                f'<div class="video"><iframe loading="lazy" src="{e(embed)}" title="{e(title)}" '
                'allow="fullscreen; picture-in-picture" allowfullscreen '
                'referrerpolicy="strict-origin-when-cross-origin"></iframe></div>'
            )
        suffix = f' {number}' if len(videos) > 1 else ''
        label = f'查看原始视频{suffix}' if chinese else f'Watch original video{suffix} at source'
        fallback = '播放器不可用时，可前往来源观看。' if chinese else 'If the player is unavailable, open the original video.'
        media.append(
            f'<p class="caption"><a href="{e(url)}" rel="noopener noreferrer">{label}</a> · {fallback}</p>'
        )
    if gallery_images:
        heading = '更多照片' if chinese else 'More views'
        label = f'打开 {name} 的照片' if chinese else f'Open {name} photo'
        gallery = ''.join(
            f'<a href="{e(url)}" aria-label="{e(label)}">{photo(url, name, chinese=chinese)}</a>'
            for url in gallery_images
        )
        media.append(f'<h2>{heading}</h2><div class="gallery">{gallery}</div>')
    return ''.join(media)


def venue_actions(links, chinese):
    actions = []
    seen = set()
    for link in links:
        if link['kind'] in ('image', 'video'):
            continue
        label = link_label(link, chinese)
        parsed = urlparse(link['url'])
        key = (label, parsed.netloc, parsed.path.rstrip('/'))
        if key in seen:
            continue
        seen.add(key)
        actions.append(
            f'<a class="action" href="{e(link["url"])}" rel="noopener noreferrer">{e(label)}</a>'
        )
    return ''.join(actions)


def venue_detail(record, links, images, category, chinese, alternate):
    name = record['name']
    city = '拉斯维加斯' if chinese else 'Las Vegas'
    hero = images[0] if images else None
    intro = (
        navigation(chinese, alternate, detail=True)
        + f'<span class="eyebrow">{e(category)} · {city}</span><h1>{e(name)}</h1>'
        + f'<p class="lead">{e(record["description"] or "")}</p>'
        + photo(hero, name, hero=True, chinese=chinese)
    )
    if hero:
        photo_label = '查看原图' if chinese else 'Open original photo'
        photo_credit = '照片来自 No Cover Nightclubs。' if chinese else 'Photo via No Cover Nightclubs.'
        intro += f'<p class="caption"><a href="{e(hero)}">{photo_label}</a> · {photo_credit}</p>'

    videos = [link['url'] for link in links if link['kind'] == 'video']
    media = venue_media(name, videos, images[1:], chinese)
    if media:
        heading = '场馆实景' if chinese else 'Step inside'
    else:
        heading = '了解场馆' if chinese else 'Explore the venue'
        message = (
            '可前往来源查看更多照片和最新场馆信息。' if chinese
            else 'Visit the source for more photos and current venue information.'
        )
        media = f'<p class="lead">{message}</p>'

    facts = fact_list(record['facts'], chinese)
    directory = fact_list(record.get('directory_facts', {}), chinese, directory=True)
    directory_details = ''
    if directory:
        summary = '对照目录信息' if chinese else 'Compare directory listing'
        note = (
            '目录与详情页的信息可能有出入。请向场馆确认当前营业时间。' if chinese
            else 'The directory and detail page may differ. Confirm current hours with the venue.'
        )
        directory_details = f'<details><summary>{summary}</summary><dl>{directory}</dl><p class="note">{note}</p></details>'
    facts_heading = '基本信息' if chinese else 'At a glance'
    main = (
        f'<div class="content-layout"><section><h2>{heading}</h2>{media}'
        f'<div class="actions">{venue_actions(links, chinese)}</div></section>'
        f'<aside class="panel"><h2>{facts_heading}</h2><dl>{facts}</dl>{directory_details}</aside></div>'
    )

    source = record['source']
    source_label = '来源：' if chinese else 'Source: '
    observed_label = '采集于' if chinese else 'Observed'
    disclaimer = (
        '营业时间和入场规定可能调整。媒体版权归各权利人所有。' if chinese
        else 'Hours and policies can change. Media belongs to its respective owners.'
    )
    record_url = '../../data/venues/zh-CN/' if chinese else '../data/venues/'
    record_label = '简中 JSON 记录' if chinese else 'JSON record'
    footer = (
        f'<footer>{source_label}<a href="{e(source["url"])}">No Cover Nightclubs</a> · '
        f'{observed_label} {e(source["observed_at"])}<p>{disclaimer}</p>'
        f'<a href="{record_url}{e(record["id"])}.json">{record_label}</a>{branding(chinese)}</footer>'
    )
    return page(name, intro + main + review_notes(record.get('quality', {}), chinese) + footer, chinese)


def venue_card(record, hero, category, chinese):
    return (
        f'<a class="card" href="{e(record["id"])}.html">{photo(hero, record["name"], chinese=chinese)}'
        f'<div class="card-content"><span class="badge">{e(category)}</span>'
        f'<h3>{e(record["name"])}</h3><p>{e(record["facts"].get("location", ""))}</p></div></a>'
    )


def catalog_page(cards, chinese, alternate):
    if chinese:
        title = '拉斯维加斯场馆'
        header = f'<h1>{title}</h1><p class="lead">浏览 {len(cards)} 家泳池俱乐部与夜店。</p>'
        search_label = '搜索场馆或酒店'
        placeholder = '例如 Omnia、Encore 或夜店'
        empty = '未找到符合条件的场馆。试试其他场馆或酒店名称。'
        credit = (
            '场馆资料和媒体来自 <a href="https://nocovernightclubs.com/nightclubs/">No Cover Nightclubs</a>。'
            '请向场馆确认当前营业时间和入场规定。'
        )
    else:
        title = 'Vegas venues'
        header = (
            '<span class="eyebrow">The Las Vegas collection</span><h1>Find your next<br>scene.</h1>'
            f'<p class="lead">From poolside afternoons to late-night dance floors. Explore {len(cards)}'
            ' Vegas venues, with a closer look inside.</p>'
        )
        search_label = 'Find a venue or hotel'
        placeholder = 'Try Omnia, Encore or dayclub'
        empty = 'No venues match. Try another name or hotel.'
        credit = (
            'Venue information and media via <a href="https://nocovernightclubs.com/nightclubs/">'
            'No Cover Nightclubs</a>. Verify current hours and entry policies with the venue.'
        )
    body = (
        navigation(chinese, alternate) + header
        + f'<div class="searchbox"><label for="search">{search_label}</label>'
        + f'<input id="search" placeholder="{placeholder}" type="search"></div><p id="empty" hidden>{empty}</p>'
        + f'<section class="grid">{"".join(cards)}</section><footer>{credit}{branding(chinese)}</footer>'
        + SEARCH_SCRIPT
    )
    return page(title, body, chinese)


def read_records(directory):
    return {
        path.stem: json.loads(path.read_text(encoding='utf-8'))
        for path in sorted(directory.glob('*.json'))
        if path.name != 'index.json'
    }


def build_catalog(target, records, alternate_records, chinese=False):
    target.mkdir(parents=True, exist_ok=True)
    alternate_prefix = '../' if chinese else 'zh-CN/'
    cards = []
    for slug, record in records.items():
        alternate = f'{alternate_prefix}{slug}.html' if slug in alternate_records else None
        links = [link for link in record['links'] if safe_url(link['url'])]
        images = list(dict.fromkeys(link['url'] for link in links if link['kind'] == 'image'))
        category = record['listing_category']
        if chinese:
            category = CATEGORY_LABELS_ZH[category]
        detail = venue_detail(record, links, images, category, chinese, alternate)
        (target / f'{record["id"]}.html').write_text(detail, encoding='utf-8')
        cards.append(venue_card(record, images[0] if images else None, category, chinese))
    alternate_index = f'{alternate_prefix}index.html' if alternate_records else None
    (target / 'index.html').write_text(catalog_page(cards, chinese, alternate_index), encoding='utf-8')


def build(root=ROOT):
    source = root / 'data/venues'
    out = root / 'site'
    target = out / 'venues'
    dest = out / 'data/venues'
    english_source = source / 'en'
    if not english_source.is_dir():
        english_source = source
    english = read_records(english_source)
    chinese = read_records(source / 'zh-CN')

    build_catalog(target, english, chinese)
    shutil.copyfile(root / 'assets/venues.css', target / 'style.css')
    if chinese:
        build_catalog(target / 'zh-CN', chinese, english, chinese=True)
        shutil.copytree(source / 'zh-CN', dest / 'zh-CN', dirs_exist_ok=True, ignore=shutil.ignore_patterns('.gitkeep'))

    english_dest = dest / 'en'
    english_dest.mkdir(parents=True, exist_ok=True)
    for slug in english:
        filename = f'{slug}.json'
        shutil.copyfile(english_source / filename, dest / filename)
        shutil.copyfile(english_source / filename, english_dest / filename)
    index = [
        {
            'id': record['id'],
            'name': record['name'],
            'type': record['listing_category'],
            'detail_url': f'venues/{record["id"]}.html',
            'json_url': f'data/venues/{record["id"]}.json',
        }
        for record in english.values()
    ]
    (dest / 'index.json').write_text(json.dumps({'venues': index}, indent=2) + '\n', encoding='utf-8')
    return len(english)


if __name__ == '__main__':
    print(f'Built venue catalog ({build()} venues)')
