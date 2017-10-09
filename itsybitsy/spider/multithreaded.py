import threading
import warnings
import logging
try: # python 3
    import queue
except ImportError: # python 2
    import Queue as queue

import requests

from itsybitsy import util

logger = logging.getLogger("itsybitsy")


class StopCrawling(Exception):
    pass


def crawl(base_url, only_go_deeper=True, max_depth=5, max_retries=10, timeout=10, strip_fragments=True, max_connections=100, session=None):
    """
    Arguments
    ---------

    Known issues
    ------------
    - When using max_depth and multiple threads, some pages that
      can be reached through multiple paths might get excluded
    - There are no guarantees on a particular ordering
    """
    if session is None:
        session = requests.Session()
        close_session = True
    else:
        close_session = False

    try:
        with session.get(base_url) as response:
            real_base_url = str(response.url)
        yield real_base_url

        # holds all pages to be crawled and their distance from the base
        page_queue = queue.Queue()
        page_queue.put((base_url,0))

        # set to check which sites have been visited already
        visited = set([real_base_url])
        visited_lock = threading.Lock()

        # second queue to be yielded from
        found_urls = queue.Queue()
        found_urls.put(base_url)

        def visit_link():
            page_url, page_depth = page_queue.get()
            try:
                if page_url is None:
                    raise StopCrawling
                if max_depth and page_depth >= max_depth:
                    return

                logger.debug("Visiting %s" % page_url)

                num_retries = 0
                while True: # retry on failure
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

                for link in util.get_all_valid_links(html, base_url=real_page_url):
                    if only_go_deeper and not util.url_is_deeper(link, real_base_url):
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
            finally: # stop worker threads
                for _ in range(max_connections):
                    page_queue.put((None,None))

        else:
            while not page_queue.empty():
                visit_link()
                while not found_urls.empty():
                    yield found_urls.get()
    finally:
        if close_session:
            session.close()
