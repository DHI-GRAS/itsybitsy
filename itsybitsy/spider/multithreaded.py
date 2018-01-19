import threading
import warnings
import logging

try:  # python 3
    import queue
except ImportError:  # python 2
    import Queue as queue

import lxml.html
import requests

from itsybitsy import util
from itsybitsy.url_normalize import url_normalize

logger = logging.getLogger("itsybitsy")


class StopCrawling(Exception):
    pass


def crawl(base_url, only_go_deeper=True, max_depth=5, max_retries=10, timeout=10,
          strip_fragments=True, max_connections=100, session=None, auth=None):
    """Multi-threaded implementation of the itsybitsy web crawler.

    For use with Python versions below 3.5.

    Parameters
    ---------
    base_url : str
        Starting point for crawler
    only_go_deeper : bool
        Only visit links that start with the same path as the base url (default: True)
    max_depth : int
        Maximum depth from base_url to visit (default: 5)
    max_retries : int
        Maximum number of retries when sending GET requests (default: 10)
    timeout : float
        Timeout in seconds when sending GET requests (default: 10)
    strip_fragments : bool
        Treat URLs that only differ in fragments (such as `test.html#hi` and
        `test.html#hello`) as equal (default: True)
    max_connections : int
        Maximum number of concurrent connections (default: 100)
    session : requests.Session
        Session to use for sending requests (default: create a new session)
    auth : tuple
        Authentication object used when opening a session (has no effect when session is given)

    Note
    ----
    By switching to Python 3.5 or above, you can instead use our awesome
    asynchronous crawler based on asyncio and aiohttp!

    """
    if session is None:
        session = requests.Session()
        if auth:
            session.auth = auth
        close_session = True
    elif isinstance(session, requests.Session):
        close_session = False
    else:
        raise TypeError('session argument must be requests.Session object')

    try:
        with session.get(base_url, stream=True) as response:
            base_url = url_normalize(str(response.url))
        yield base_url

        # holds all pages to be crawled and their distance from the base
        page_queue = queue.Queue()
        page_queue.put((base_url, 0))

        # set to check which sites have been visited already
        visited = set([base_url])
        visited_lock = threading.Lock()

        # second queue to be yielded from
        found_urls = queue.Queue()

        def visit_link():
            page_url, page_depth = page_queue.get()
            try:
                if page_url is None:
                    raise StopCrawling
                if max_depth and page_depth >= max_depth:
                    return

                logger.debug("Visiting %s" % page_url)

                num_retries = 0
                while True:  # retry on failure
                    try:
                        with session.get(page_url, stream=True, timeout=timeout) as response:
                            response.raise_for_status()

                            if 'text/html' not in response.headers['content-type']:
                                return

                            html = response.content
                            real_page_url = str(response.url)
                            break

                    except requests.RequestException as e:
                        if max_retries and num_retries < max_retries:
                            num_retries += 1
                            logger.debug("Encountered error: %s - retrying (%d/%d)" % (e, num_retries, max_retries))
                        else:
                            warnings.warn("Error when querying %s: %s" % (page_url, e))
                            return

                if not html:
                    return

                dom = lxml.html.fromstring(html)
                page_base_url = util.get_base_from_dom(dom, real_page_url)

                for link in util.get_all_valid_links_from_dom(dom, base_url=page_base_url):
                    if only_go_deeper and not util.url_is_deeper(link, base_url):
                        continue
                    if strip_fragments:
                        link = util.strip_fragments(link)
                    with visited_lock:
                        if link in visited:
                            continue
                        visited.add(link)
                    page_queue.put((link, page_depth+1))
                    found_urls.put(link)

            finally:
                page_queue.task_done()

        def crawl_forever():
            while True:
                try:
                    visit_link()
                except StopCrawling:
                    break

        if max_connections:
            try:
                for _ in range(max_connections):
                    worker_thread = threading.Thread(target=crawl_forever)
                    worker_thread.daemon = True
                    worker_thread.start()
                main_thread = threading.Thread(target=page_queue.join)
                main_thread.daemon = True
                main_thread.start()
                while main_thread.is_alive() or not found_urls.empty():
                    try:
                        yield found_urls.get(timeout=1)
                    except queue.Empty:
                        pass
                main_thread.join()
            finally:  # stop worker threads
                for _ in range(max_connections):
                    page_queue.put((None, None))

        else:
            while not page_queue.empty():
                visit_link()
                while not found_urls.empty():
                    yield found_urls.get()

    finally:
        if close_session:
            session.close()
