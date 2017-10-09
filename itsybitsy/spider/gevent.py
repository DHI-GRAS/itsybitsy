import warnings
import logging

import gevent
from gevent import monkey as curious_george
from gevent.pool import Pool
curious_george.patch_all(thread=False, select=False)

import requests

from itsybitsy import util

logger = logging.getLogger("itsybitsy")


def crawl(base_url, only_go_deeper=True, max_depth=5, max_retries=10, timeout=600, strip_fragments=True, max_connections=100, session=None):
    pool = Pool(max_connections)

    if session is None:
        session = requests.Session()
        close_session = True
    else:
        close_session = False

    try:
        real_base_url = str(session.get(base_url).url)
        yield real_base_url

        visited = set([real_base_url])


        def visit_link(session, page_url):
            print("Visiting %s" % page_url)
            num_retries = 0
            while True: # retry on failure
                try:
                    with session.get(page_url, stream=True) as response:
                        if "text/html" not in response.headers["content-type"]:
                            return []
                        html = response.text
                        real_page_url = str(response.url)
                        break

                except Exception as e:
                    if max_retries and num_retries < max_retries:
                        num_retries += 1
                        logger.debug("Encountered error: %s - retrying (%d/%d)" % (e, num_retries, max_retries))
                    else:
                        warnings.warn("Error when querying %s: %s" % (page_url, repr(e)))
                        return []

            new_links = []
            for link in util.get_all_valid_links(html, base_url=real_page_url):
                if only_go_deeper and not util.url_is_deeper(link, real_base_url):
                    continue
                if strip_fragments:
                    link = util.strip_fragments(link)
                if link in visited:
                    continue
                visited.add(link)
                new_links.append(link)
            return new_links

        links_to_process = [real_base_url]
        current_depth = 1

        while links_to_process:
            if max_depth and current_depth > max_depth:
                break

            futures = pool.imap_unordered(lambda x: visit_link(session, x), links_to_process)
            links_to_process = []
            for new_links in futures:
                links_to_process.extend(new_links)
                yield from new_links

            current_depth += 1
    finally:
        if close_session:
            session.close()
