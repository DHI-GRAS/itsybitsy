try:
    import urlparse
except ImportError:
    from urllib import parse as urlparse
import logging

import lxml.html

from itsybitsy.url_normalize import url_normalize

logger = logging.getLogger("itsybitsy")


def strip_fragments(url):
    return urlparse.urldefrag(url)[0]


def is_relative_link(url):
    return not urlparse.urlparse(url).netloc


def link_is_http(url):
    return urlparse.urlparse(url).scheme.startswith("http")


def normalize_url(url):
    if is_relative_link(url):
        raise ValueError("cannot normalize relative path: %s" % url)
    return url_normalize(url)


def url_is_deeper(child, parent):
    child_components = urlparse.urlsplit(url_normalize(child))
    parent_components = urlparse.urlsplit(url_normalize(parent))
    return (
        child_components.netloc == parent_components.netloc
        and child_components.path.startswith(parent_components.path)
    )


def get_all_valid_links_from_dom(dom, base_url, convert_to_absolute=True, only_http=True):
    links = set(dom.xpath('//a/@href'))
    for link in links:
        link = link.strip()
        if not link:
            continue
        if convert_to_absolute and is_relative_link(link):
            link = urlparse.urljoin(base_url, link)
        if only_http and not link_is_http(link):
            continue
        try:
            link = normalize_url(link)
        except ValueError:
            logger.info("encountered malformed link: %s" % link)
            continue
        yield link


def get_base_from_dom(dom, page_url):
    base = dom.xpath('//head/base/@href')
    if base:
        return urlparse.urljoin(page_url, base[0].strip())
    return page_url
