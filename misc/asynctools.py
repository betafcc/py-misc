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


class AsCompletedQueue:
    def __init__(self, *, loop=None, timeout=None):
        self._loop = loop if loop is not None else asyncio.get_event_loop()
        self._todo = set()
        self._done = asyncio.Queue(loop=self._loop)
        self._timeout_handle = None
        if timeout is not None:
            self._timeout_handle = loop.call_later(timeout, self._on_timeout)
        self._qsize = 0

    def qsize(self):
        return self._qsize

    def get_nowait(self):
        if not self._qsize:
            raise asyncio.QueueEmpty('No more futures to give')
        else:
            self._qsize -= 1
            return self._wait_for_one()

    def get_all_nowait(self):
        acc = []
        while True:
            try:
                acc.append(self.get_nowait())
            except asyncio.QueueEmpty:
                break
        return acc

    def put_nowait(self, awaitable):
        task = self._loop.create_task(awaitable)
        self._todo.add(task)
        task.add_done_callback(self._on_completion)
        self._qsize += 1

    def submit(self, f, *args, **kwargs):
        self.put_nowait(f(*args, **kwargs))

    def submit_flatten(self, f, *args, **kwargs):
        self.submit(flatten(f), *args, **kwargs)

    def iter_until_empty(self):
        for coro in self.get_until_empty():
            yield self._loop.run_until_complete(coro)

    async def aiter_until_empty(self):
        for coro in self.get_until_empty():
            yield await coro

    def get_until_empty(self):
        while True:
            try:
                coro = self.get_nowait()
            except asyncio.QueueEmpty:
                break
            yield coro

    def _on_timeout(self):
        for f in self._todo:
            f.remove_done_callback(self._on_completion)
            self._done.put_nowait(None)
        self._todo.clear()
        self._qsize = 0

    def _on_completion(self, f):
        if not self._todo:
            return
        self._todo.remove(f)
        self._done.put_nowait(f)
        if not self._todo and self._timeout_handle is not None:
            self._timeout_handle.cancel()

    async def _wait_for_one(self):
        f = await self._done.get()
        if f is None:
            raise asyncio.futures.TimeoutError
        return f.result()


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
