import asyncio
from functools import wraps
from collections.abc import Awaitable


def sync(f, loop=None):
    @wraps(f)
    def _sync(*args, **kwargs):
        coro = f(*args, **kwargs)
        if loop is None:
            return asyncio.run(coro)
        return loop.run_until_complete(coro)
    return _sync


async def resolve(awaitable_or_not):
    if isinstance(awaitable_or_not, Awaitable):
        return await awaitable_or_not
    return awaitable_or_not


def agnostic(f):
    @wraps(f)
    def _agnostic(*args, **kwargs):
        result = f(*args, **kwargs)
        if not isinstance(result, Awaitable):
            return result
        try:
            asyncio.get_running_loop()
            return result
        except RuntimeError:
            return asyncio.run(result)
    return _agnostic


class AsyncQueue:
    def __init__(self):
        self._done = asyncio.Queue()

    def submit(self, f, *args, **kwargs):
        async def _():
            result = await f(*args, **kwargs)
            await self._done.put(result)
            return result
        return asyncio.create_task(_())

    def get_done(self):
        return self._done.get()
