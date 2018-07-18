import asyncio
from collections.abc import Iterable

import tqdm
import aiohttp

from .asynctools import agnostic


@agnostic
async def get(urls, *args, **kwargs):
    if not isinstance(urls, Iterable):
        return await get_one(urls, *args, **kwargs)
    return await get_all(urls, *args, **kwargs)


async def get_one(*args, session=None, **kwargs):
    if session is None:
        async with aiohttp.ClientSession() as session:
            return await get_one(*args, session=session, **kwargs)
    async with session.get(*args, **kwargs) as response:
        try:
            response.body = await response.read()
            response.sucess = True
        except Exception as exception:
            response.exception = exception
            response.sucess = False
        return response


async def get_all(urls,
                  *args,
                  session=None,
                  show_progress=False,
                  pbar=None,
                  **kwargs,
                  ):
    if session is None:
        _len = len(urls)
        connector = aiohttp.TCPConnector(limit=_len, limit_per_host=_len)
        async with aiohttp.ClientSession(connector=connector) as session:
            return await get_all(
                urls,
                *args,
                session=session,
                show_progress=show_progress,
                pbar=pbar,
                **kwargs,
            )

    if show_progress and pbar is None:
        with tqdm.tqdm(total=len(urls)) as pbar:
            return await get_all(
                urls,
                *args,
                session=session,
                show_progress=show_progress,
                pbar=pbar,
                **kwargs,
            )

    async def mapper(url):
        result = await get_one(url, *args, session=session, **kwargs)
        if show_progress:
            pbar.update(1)
        return result

    return await asyncio.gather(*map(mapper, urls))
