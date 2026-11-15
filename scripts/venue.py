"""Bounded venue fact extraction. Does not execute remote markup or follow embedded URLs."""
import html
import re
from urllib.parse import urlparse

def text(value):
    return html.unescape(re.sub(r'\s+', ' ', re.sub('<[^>]+>', ' ', value))).strip()

def extract(document, url, category, observed_at):
    if urlparse(url).hostname != 'nocovernightclubs.com':
        raise ValueError('Unexpected source host')
    document = re.sub(r'<(script|style)\b.*?</\1>', '', document, flags=re.S|re.I)
    start = re.search(r'<h1\b[^>]*>(.*?)</h1>', document, re.S|re.I)
    if not start:
        raise ValueError('Missing venue heading')
    name = text(start.group(1))
    body = document[start.end():]
    # Stop before reviews/calendars/footer. Embedded event widgets contain unrelated venues.
    stop = re.search(r'<h[2-4]\b[^>]*>\s*(?:Reviews?|Contact|Upcoming)\b', body, re.I)
    if stop:
        body = body[:stop.start()]
    facts = {}
    for label in ['Location','Nights','Days','Music','Size']:
        m = re.search(r'<(?:strong|b)>\s*'+label+r':?\s*</(?:strong|b)>\s*([^<]*(?:<(?!/?(?:p|br)\b)[^>]+>[^<]*)*)',body,re.I)
        if m: facts[label.lower()] = text(m.group(1))
    links=[]
    for raw in re.findall(r'(?:href|src)=[\"\x27]([^\"\x27]+)',body,re.I):
        value=html.unescape(raw)
        parsed=urlparse(value)
        if parsed.scheme not in ['https','http']: continue
        kind='source'
        if parsed.hostname in ['www.youtube.com','youtube.com','youtu.be']: kind='video'
        elif parsed.hostname and (parsed.hostname.endswith('google.com') or parsed.hostname=='maps.app.goo.gl') and 'map' in value: kind='map'
        elif 'virtual-tour' in value or '360-tour' in value: kind='virtual_tour'
        elif re.search(r'\.(?:png|jpe?g|webp)(?:\?|$)',value,re.I): kind='image'
        item={'kind':kind,'url':value}
        if item not in links: links.append(item)
    sections=[]
    for m in re.finditer(r'<h[2-4]\b[^>]*>(.*?)</h[2-4]>(.*?)(?=<h[2-4]\b|$)',body,re.S|re.I):
        heading=text(m.group(1)); content=text(m.group(2))
        sections.append({'heading':heading,'source_url':url})
        # Extract address and operating hours as facts, never unrelated calendar data.
        if 'Located' in heading:
            address=re.search(r'\b\d{3,6}\s[^.]*Las Vegas[^.]*?\b\d{5}\b',content)
            if address: facts['address']=address.group(0)
        if re.search(r'When.*Open',heading,re.I):
            hours=re.search(r'\b(?:from\s+)?\d{1,2}(?::\d{2})?\s*(?:am|pm)\s*(?:until|to|-)\s*\d{1,2}(?::\d{2})?\s*(?:am|pm)',content,re.I)
            if hours: facts['hours']=hours.group(0)
    summary = name + ((' at '+facts['location']) if facts.get('location') else '') + '.'
    if facts.get('music'): summary += ' Listed music: '+facts['music']+'.'
    slug=urlparse(url).path.strip('/').split('/')[-1]
    return {'id':slug,'name':name,'listing_category':category,'facts':facts,'description':summary,'sections':sections,'field_provenance':{k:{'source_url':url,'retrieved_at':observed_at} for k in facts},'links':links,'source':{'url':url,'observed_at':observed_at},'quality':{'profile_parsed':True,'description_kind':'fact_summary'}}

def listing_facts(document,url):
    """Keep directory observations separate when the profile disagrees."""
    at=document.find(url)
    if at<0:return {}
    start=document.rfind('class="guest-list-item',0,at)
    end=document.find('Club Details',at)
    if start<0 or end<0:return {}
    raw=document[start:end]
    out={}
    for key,label in [('location','Location'),('days','Days Open'),('music','Music')]:
        m=re.search(r'<strong>\s*(?:<br\s*/?>\s*)?'+label+r':\s*</strong>\s*(.*?)(?=<br|</p>|<strong>)',raw,re.S|re.I)
        if m:out[key]=text(m.group(1))
    return out
