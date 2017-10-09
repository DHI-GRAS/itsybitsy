import sys

HAS_ASYNC = sys.version_info >= (3, 5)

if HAS_ASYNC:
    import itsybitsy.spider.async
    crawl = itsybitsy.spider.async.crawl
else:
    import itsybitsy.spider.multithreaded
    crawl = itsybitsy.spider.multithreaded.crawl
