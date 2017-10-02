try:
    import asyncio
    del asyncio
    HAS_ASYNCIO = True
except ImportError:
    HAS_ASYNCIO = False

import itsybitsy.sequential
import itsybitsy.multithreaded
if HAS_ASYNCIO:
    import itsybitsy.async
