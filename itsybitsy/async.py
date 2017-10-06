def crawl_website(base_url, only_go_deeper=True, max_depth=5):
    visited = set()

    real_base_url = get_real_url(base_url)

    async def visit_link(page_url, page_depth):
        async with aiohttp.ClientSession() as session:
            async with session.get(page_url) as response:
                if 'text/html' not in response.headers['content-type']:
                    return None
                real_page_url = str(response.url)
                parser = LinkFinder(real_page_url)
                parser.feed(await response.text())
                new_links = []
                for link in parser.links:
                    if only_go_deeper and not url_is_deeper(link, real_base_url):
                        continue
                    if max_depth and page_depth >= max_depth:
                        continue
                    if link in visited:
                        continue
                    visited.add(link)
                    new_links.append((link, page_depth+1))
                return new_links

    loop = asyncio.get_event_loop()
    links_to_process = [(real_base_url, 0)]
    while links_to_process:
        for link, depth in links_to_process:
            yield link
        links_to_process = loop.run_until_complete(
                                asyncio.gather(
                                    *[visit_link(link, depth) for link, depth in links_to_process]
                                )
        )
        links_to_process = [item for sublist in links_to_process for item in sublist if item]
