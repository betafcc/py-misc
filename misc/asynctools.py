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


def flatten(f):
    @wraps(f)
    def _flatten(*args, **kwargs):
        return flat(f(*args, **kwargs))
    return _flatten


async def flat(coro):
    while isinstance(coro, Awaitable):
        coro = await coro
    return coro


async def resolve(awaitable_or_not):
    if isinstance(awaitable_or_not, Awaitable):
        return await awaitable_or_not
    return awaitable_or_not


async def then(f, coro):
    return await flatten(f)(await flat(coro))


class AsyncQueue:
    def __init__(self, *args, loop=None, **kwargs):
        if loop is None:
            self._loop = asyncio.get_event_loop()
        else:
            self._loop = loop
        self._done = asyncio.Queue(*args, loop=loop, **kwargs)
        self._tasks = set()

    async def __aiter__(self):
        while True:
            close, value = await self._done.get()
            if close:
                break
            yield value

    def submit_close(self, wait=True):
        return self._loop.create_task(self._close(wait=wait))

    async def _close(self, wait=True):
        if wait:
            await self.wait_submitted()
        return await self.close_soon()

    async def wait_submitted(self):
        return await asyncio.gather(*self._tasks)

    def close_soon(self):
        return self._loop.create_task(self._done.put((True, None)))

    async def get_done(self):
        close, value = await self._done.get()
        return value

    async def _put_done(self, value):
        await self._done.put((False, value))

    def submit(self, f, *args, **kwargs):
        return self.submit_awaitable(f(*args, **kwargs))

    def submit_flatten(self, f, *args, **kwargs):
        return self.submit(flatten(f), *args, **kwargs)

    def submit_awaitable(self, awaitable):
        return self._register_as_task(self._wrap_awaitable(awaitable))

    async def _wrap_awaitable(self, awaitable):
        result = await awaitable
        await self._put_done(result)
        return result

    def _register_as_task(self, awaitable):
        task = self._loop.create_task(awaitable)
        self._tasks.add(task)
        task.add_done_callback(lambda _: self._tasks.remove(task))
        return task


async def as_completed_map(f, *its, loop=None):
    if loop is None:
        loop = asyncio.get_event_loop()

    _ = map(f, *its)
    _ = map(loop.create_task, _)
    _ = asyncio.as_completed(list(_))

    for completed in _:
        yield await completed


class aiter_to_iter:
    def __init__(self, it, loop=None):
        if loop is None:
            self._loop = asyncio.get_event_loop()
        else:
            self._loop = loop
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
        self._loop.run_until_complete(self._enqueue_each_done())

    async def _enqueue_each_done(self):
        try:
            async for el in self._it:
                self._queue.put((False, el))
            self._queue.put((True, None))
        except Exception as e:
            self._queue.put((True, e))
