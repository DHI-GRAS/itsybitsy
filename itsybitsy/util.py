import urlparse


def is_relative_link(url):
    return not urlparse.urlparse(url).netloc


def normalize_url(url):
    if is_relative_link(url):
        raise ValueError("cannot normalize relative path")
    return url_normalize.url_normalize(url)


def url_is_deeper(child, parent, normalizer=url_normalize.url_normalize):
    child_components = urlparse.urlsplit(normalizer(child))
    parent_components = urlparse.urlsplit(normalizer(parent))
    return (
        child_components.netloc == parent_components.netloc
        and child_components.path.startswith(parent_components.path)
    )


class LinkFinder(HTMLParser):
    """Parses an HTML file and build a list of links.

    Links are stored into the 'links' list. If `base_url` is given, relative
    links are resolved into absolute paths.
    """
    def __init__(self, base_url=None, link_tag='a', link_attr='href'):
        HTMLParser.__init__(self)

        self._base_url = base_url
        self._link_tag = link_tag
        self._link_attr = link_attr
        self.links = []
        self._seen_links = set()

    def handle_starttag(self, tag, attrs):
        if tag == self._link_tag:
            for key, value in attrs:
                if key != self._link_attr:
                    continue
                if not value:
                    continue

                if self._base_url and is_relative_link(value):
                    value = urlparse.urljoin(self._base_url, value)
                value = normalize_url(value)

                if value not in self._seen_links:
                    self.links.add(value)
                    self._seen_links.add(value)
