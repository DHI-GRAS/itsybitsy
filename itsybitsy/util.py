try:
    import urlparse
except ImportError:
    from urllib import parse as urlparse

import lxml.html

from itsybitsy.url_normalize import url_normalize


def strip_fragments(url):
    return urlparse.urldefrag(url)[0]


def is_relative_link(url):
    return not urlparse.urlparse(url).netloc


def link_is_http(url):
    return urlparse.urlparse(url).scheme.startswith("http")


def normalize_url(url):
    if is_relative_link(url):
        raise ValueError("cannot normalize relative path")
    return url_normalize(url)


def url_is_deeper(child, parent):
    child_components = urlparse.urlsplit(url_normalize(child))
    parent_components = urlparse.urlsplit(url_normalize(parent))
    return (
        child_components.netloc == parent_components.netloc
        and child_components.path.startswith(parent_components.path)
    )

def get_all_valid_links(html, base_url, convert_to_absolute=True, only_http=True):
    dom = lxml.html.fromstring(html)
    links = set(dom.xpath('//a/@href'))
    for link in links:
        link = link.strip()
        if not link:
            continue
        if convert_to_absolute and is_relative_link(link):
            link = urlparse.urljoin(base_url, link)
        if only_http and not link_is_http(link):
            continue
        link = normalize_url(link)
        yield link


#
# class LinkFinder(HTMLParser):
#     """Parses an HTML file and build a list of links.
#     Links are stored into the 'links' list. If `base_url` is given, relative
#     links are resolved into absolute paths.
#     """
#     def __init__(self, base_url=None, link_tag='a', link_attr='href'):
#         HTMLParser.__init__(self)
#
#         self._base_url = normalize_url(base_url)
#         self._link_tag = link_tag
#         self._link_attr = link_attr
#         self.links = []
#         self._seen_links = set()
#
#     def handle_starttag(self, tag, attrs):
#         if tag == self._link_tag:
#             for key, value in attrs:
#                 if key != self._link_attr:
#                     continue
#                 if not value:
#                     continue
#
#                 value = value.strip()
#
#                 if self._base_url and is_relative_link(value):
#                     value = urlparse.urljoin(self._base_url, value)
#
#                 if not link_is_http(value):
#                     continue
#
#                 try:
#                     value = normalize_url(value)
#                 except ValueError:
#                     continue
#
#                 if value not in self._seen_links:
#                     self.links.append(value)
#                     self._seen_links.add(value)
