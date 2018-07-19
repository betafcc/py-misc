import asyncio
from queue import Queue
from functools import wraps
from threading import Thread
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
    def __init__(self, *args, loop=None, **kwargs):
        if loop is None:
            self._loop = asyncio.get_event_loop()
        else:
            self._loop = loop
        self._done = asyncio.Queue(*args, loop=loop, **kwargs)

    def submit(self, f, *args, **kwargs):
        async def _():
            result = await f(*args, **kwargs)
            await self._done.put(result)
            return result
        return self._loop.create_task(_())

    def get_done(self):
        return self._done.get()


async def as_completed_map(f, *its, loop=None):
    if loop is None:
        loop = asyncio.get_event_loop()

    _ = map(f, *its)
    _ = map(loop.create_task, _)
    _ = asyncio.as_completed(list(_))

    for completed in _:
        yield await completed


class aiter_to_iter:
    def __init__(self, it):
        self._it = it
        self._queue = Queue()

    def __iter__(self):
        t = Thread(target=self._worker)
        t.start()
        while True:
            done, value = self._queue.get()
            if done:
                break
            yield value

        if value is not None:
            raise value

        t.join()

    def _worker(self):
        async def enqueue_iter():
            try:
                async for el in self._it:
                    self._queue.put((False, el))
                self._queue.put((True, None))
            except Exception as e:
                self._queue.put((True, e))

        asyncio.run(enqueue_iter())
