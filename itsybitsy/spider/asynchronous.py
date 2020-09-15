import asyncio
import warnings
import logging
import functools

import aiohttp
import lxml.html

from itsybitsy import util
from itsybitsy.url_normalize import url_normalize

logger = logging.getLogger("itsybitsy")


async def crawl_async(base_url, only_go_deeper=True, max_depth=5, max_retries=10, timeout=10,
                      strip_fragments=True, max_connections=100, session=None, auth=None):
    """A powerful, asynchronous webcrawler based on asyncio and aiohttp.

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
    session : aiohttp.Session
        Session to use for sending requests (default: create a new session)
    auth : tuple
        Authentication object used when opening a session (has no effect when session is given)

    Note
    ----
    Due to a bug in aiohttp, performance will degrade when setting a connection
    limit for the used session. Consider specifying the `max_connections` keyword
    instead.

    """
    lock = asyncio.Semaphore(max_connections)

    if session is None:
        connector = aiohttp.TCPConnector(limit=None, verify_ssl=False)
        if auth is None:
            session = aiohttp.ClientSession(connector=connector)
        else:
            session = aiohttp.ClientSession(connector=connector, auth=aiohttp.BasicAuth(*auth))
        close_session = True
    elif isinstance(session, aiohttp.ClientSession):
        close_session = False
    else:
        raise TypeError('session argument must be aiohttp.ClientSession object')

    try:
        async with session.get(base_url) as response:
            base_url = url_normalize(str(response.url))

        yield base_url

        visited = set([base_url])

        async def get_all_links(page_url, page_depth):
            logger.debug("Visiting %s", page_url)
            retry = True
            num_retries = 0
            while retry:  # retry on failure
                try:
                    async with lock:
                        async with session.get(page_url, timeout=timeout) as response:
                            try:
                                response.raise_for_status()
                            except aiohttp.ClientError as e:
                                if max_retries and num_retries < max_retries:
                                    num_retries += 1
                                    logger.debug("Encountered error: %s - retrying (%d/%d)",
                                                 e, num_retries, max_retries)
                                    continue
                                else:
                                    warnings.warn("Error when querying %s: %s"
                                                  % (page_url, repr(e)))
                                    return []
                            if "text/html" not in response.headers.get("content-type", ""):
                                return []
                            html = await response.read()
                            real_page_url = str(response.url)
                            retry = False

                except asyncio.TimeoutError as e:
                    if max_retries and num_retries < max_retries:
                        num_retries += 1
                        logger.debug("Encountered error: %s - retrying (%d/%d)",
                                     e, num_retries, max_retries)
                    else:
                        warnings.warn("Error when querying %s: %s" % (page_url, repr(e)))
                        return []

                except Exception:
                    warnings.warn("Critical error when fetching: %s" % page_url)
                    return []

            if not html:
                return []

            dom = lxml.html.fromstring(html)
            page_base_url = util.get_base_from_dom(dom, real_page_url)

            new_links = []
            all_links = list(util.get_all_valid_links_from_dom(dom, base_url=page_base_url))
            logger.debug("Found %d links" % len(all_links))
            for link in all_links:
                if only_go_deeper and not util.url_is_deeper(link, base_url):
                    continue
                if strip_fragments:
                    link = util.strip_fragments(link)
                if link in visited:
                    continue
                visited.add(link)
                new_links.append((link, page_depth+1))

            return new_links

        links_to_process = [(base_url, 1)]
        tasks_pending = set()

        while links_to_process or tasks_pending:
            for link, current_depth in links_to_process:
                if max_depth and current_depth > max_depth:
                    continue
                tasks_pending.add(get_all_links(link, current_depth))

            links_to_process = []
            tasks_done, tasks_pending = await asyncio.wait(tasks_pending, timeout=0)
            for future in tasks_done:
                new_links = future.result()
                links_to_process.extend(new_links)
                for link, _ in new_links:
                    yield link

    finally:
        if close_session:
            await session.close()


@functools.wraps(crawl_async)
def crawl(*args, **kwargs):
    loop = asyncio.get_event_loop()
    crawler = crawl_async(*args, **kwargs).__aiter__()
    try:
        while True:
            link = crawler.__anext__()
            yield loop.run_until_complete(link)
    except StopAsyncIteration:
        return
    finally:
        loop.run_until_complete(crawler.aclose())
