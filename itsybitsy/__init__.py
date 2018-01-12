import sys

HAS_ASYNC = sys.version_info >= (3, 5)

if HAS_ASYNC:
    import itsybitsy.spider.asynchronous
    crawl = itsybitsy.spider.asynchronous.crawl
    crawl_async = itsybitsy.spider.asynchronous.crawl_async
else:
    import itsybitsy.spider.multithreaded
    crawl = itsybitsy.spider.multithreaded.crawl
