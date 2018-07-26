import asyncio

import tqdm
import aiohttp
import dateparser
from parsel import Selector

from .asynctools import agnostic


@agnostic
async def scrape(url, *args, **kwargs):
    if isinstance(url, str) and url.startswith('http'):
        if 'session' not in kwargs:
            kwargs.update(session={'raise_for_status': True})

        response = await get_one(url, *args, **kwargs)
        html = response.body.decode(response.charset)

        return Selector(text=html, base_url=url)

    else:
        try:
            return Selector(text=url)
        except TypeError:
            return Selector(text=url.body.decode(url.charset))


@agnostic
async def get(urls, *args, **kwargs):
    if isinstance(urls, str):
        return await get_one(urls, *args, **kwargs)
    return await get_all(urls, *args, **kwargs)


async def get_one(*args, session=None, **kwargs):
    if session is None:
        session = {}

    if isinstance(session, dict):
        async with aiohttp.ClientSession(**session) as session:
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
        session = {}

    if isinstance(session, dict):
        if 'connector' not in session:
            _len = len(urls)
            connector = aiohttp.TCPConnector(limit=_len, limit_per_host=_len)
            session = {'connector': connector, **session}

        async with aiohttp.ClientSession(**session) as session:
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


@agnostic
async def get_proxies():
    document = await scrape('https://www.sslproxies.org')

    keys = 'ip port code country anonymity google https last_checked'
    keys = keys.split()

    acc = []
    trs = document.css('#proxylisttable tr')[1:-1]
    for tr in trs:
        tds = (td.css('::text').extract_first() for td in tr.css('td'))
        d = dict(zip(keys, tds))

        d['google'] = _try(lambda: y_n[d['google']])
        d['https'] = _try(lambda: y_n[d['https']])
        d['last_checked'] = _try(lambda: dateparser.parse(d['last_checked']))

        acc.append(d)
    return acc


def _try(f, default=None):
    try:
        return f()
    except Exception:
        return default
