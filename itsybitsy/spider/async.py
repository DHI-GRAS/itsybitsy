import asyncio
import warnings
import logging

import aiohttp

from itsybitsy import util

logger = logging.getLogger("itsybitsy")


def crawl(base_url, only_go_deeper=True, max_depth=5, max_retries=10, timeout=600, strip_fragments=True, max_connections=100, session=None):
    lock = asyncio.Semaphore(max_connections)
    loop = asyncio.get_event_loop()

    if session is None:
        connector = aiohttp.TCPConnector(limit=None, verify_ssl=False)
        session = aiohttp.ClientSession(connector=connector, loop=loop)
        close_session = True
    else:
        close_session = False

    try:
        real_base_url = str(loop.run_until_complete(session.get(base_url)).url)
        yield real_base_url

        visited = set([real_base_url])


        async def visit_link(session, page_url):
            logger.debug("Visiting %s" % page_url)
            num_retries = 0
            while True: # retry on failure
                try:
                    async with lock:
                        async with session.get(page_url) as response:
                            if "text/html" not in response.headers.get("content-type", ""):
                                return []
                            html = await response.read()
                            real_page_url = str(response.url)
                            break

                except (asyncio.TimeoutError, aiohttp.ClientError) as e:
                    if max_retries and num_retries < max_retries:
                        num_retries += 1
                        logger.debug("Encountered error: %s - retrying (%d/%d)" % (e, num_retries, max_retries))
                    else:
                        warnings.warn("Error when querying %s: %s" % (page_url, repr(e)))
                        return []

                except ValueError:
                    warnings.warn("encountered malformed link: %s" % page_url)
                    return []

            if not html:
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

            futures = [visit_link(session, link) for link in links_to_process]
            links_to_process = []
            for task in asyncio.as_completed(futures):
                new_items = loop.run_until_complete(task)
                links_to_process.extend(new_items)
                yield from new_items

            current_depth += 1

    finally:
        if close_session:
            session.close()
