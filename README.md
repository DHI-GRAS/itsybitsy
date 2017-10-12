# itsybitsy
A minimal, concurrent web scraper for Python

## Requirements

`itsybitsy` features two implementations of the same crawling algorithm: One based
on `asyncio` and `aiohttp` that is only compatible with Python 3.5 and above, and a
`requests`-based, multithreaded implementation that is supported by most other Python
versions.

The requirements of `itsybitsy` are thus dependent on which Python version you intend
to use. For Python 3.5 and above, you will have to install `aiohttp`, `async_generator`,
and `lxml`, e.g. via

```
pip install aiohttp aiodns cchardet lxml async_generator
```

For the multithreaded version, you need to install `requests` and `lxml` via

```
pip install requests lxml
```

## Usage

`itsibitsy` provides a single function, `crawl`. The asynchronous version of the
crawler also supplies a coroutine called `crawl_async` that you can use inside
`async for` from other coroutines.
