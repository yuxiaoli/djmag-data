"""Offline scope discovery only: never fetch historical ranking editions."""
import re
from urllib.parse import urljoin, urlparse
BASE='https://djmag.com'
def current_year_links(html,year):
    links={urljoin(BASE,u) for u in re.findall(r'href=["\']([^"\']+)["\']',html)}
    return sorted(u for u in links if urlparse(u).hostname=='djmag.com' and re.fullmatch(r'/top100djs/'+str(year)+r'(?:/.*)?',urlparse(u).path))
