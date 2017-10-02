import threading
import warnings
try: # python 3
    import queue
except ImportError: # python 2
    import Queue as queue

import requests


class StopCrawling(Exception):
    pass


def crawl_page(base_url, session=None, max_depth=None, only_go_deeper=True, crawl_jobs=None, max_retries=10):
    """
    Arguments
    ---------

    Known issues
    ------------
    - When using max_depth and multiple threads, some pages that
      can be reached through multiple paths might get excluded
    - There are no guarantees on a particular ordering
    """
    base_url = normalize_url(base_url)

    if session is None:
        session = requests.Session()

    # holds all pages to be crawled and their distance from the base
    page_queue = queue.Queue()
    page_queue.put((base_url,0))

    # set to check which sites have been visited already
    visited = set([base_url])
    visited_lock = threading.Lock()

    #
    found_urls = queue.Queue()
    found_urls.put(base_url)

    def crawl():
        page_url, page_depth = page_queue.get()
        try:
            if page_url is None:
                raise StopCrawling
            if max_depth and page_depth >= max_depth:
                return

            retry = True
            num_retries = 0

            while retry:
                try:
                    with session.get(page_url, stream=True) as response:
                        response.raise_for_status()

                        if 'text/html' not in response.headers['content-type']:
                            break

                        parser = LinkFinder(page_url)
                        parser.feed(response.text)

                    for link in parser.links:
                        if only_go_deeper and not url_is_deeper(link, page_url):
                            continue
                        with visited_lock:
                            if link in visited:
                                continue
                            visited.add(link)
                        page_queue.put((link, page_depth+1))
                        found_urls.put(link)

                    retry = False

                except requests.RequestException as e:
                    if num_retries < max_retries:
                        num_retries += 1
                        warnings.warn("Encountered error: %s - retrying (%d/%d)" % (e, num_retries, max_retries))
                    else:
                        raise
        finally:
            page_queue.task_done()


    def crawl_forever():
        while True:
            try:
                crawl()
            except StopCrawling:
                break


    if crawl_jobs:
        try:
            for _ in range(crawl_jobs):
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
            for _ in range(crawl_jobs):
                page_queue.put((None,None))

    else:
        while not page_queue.empty():
            crawl()
            while not found_urls.empty():
                yield found_urls.get()
