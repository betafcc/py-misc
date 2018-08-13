import collections.abc
from itertools import cycle
from functools import partial
from types import SimpleNamespace

import aiohttp
import dateparser
from parsel import Selector
from fake_useragent import UserAgent

from .asynctools import agnostic


@agnostic
async def scrape(url, *args, **kwargs):
    if isinstance(url, str) and url.startswith("http"):
        if "session" not in kwargs:
            kwargs.update(session={"raise_for_status": True})

        response = await get(url, *args, **kwargs)
        html = response.body.decode(response.charset)

        return Selector(text=html, base_url=url)

    else:
        try:
            return Selector(text=url)
        except TypeError:
            return Selector(text=url.body.decode(url.charset))


async def request(method, url, *args, session=None, **kwargs):
    if session is None:
        session = {}
    if isinstance(session, dict):
        async with aiohttp.ClientSession(**session) as session:
            return await request(method, url, *args, session=session, **kwargs)
    async with session.request(method, url, *args, **kwargs) as response:
        await response.read()
        return response


locals().update(
    **{method: partial(request, method) for method in ["get", "post", "put"]}
)


@agnostic
async def get_proxies():
    document = await scrape("https://www.sslproxies.org")

    keys = "ip port code country anonymity google https last_checked"
    keys = keys.split()

    y_n = {"yes": True, "no": False}

    acc = []
    trs = document.css("#proxylisttable tr")[1:-1]
    for tr in trs:
        tds = (td.css("::text").extract_first() for td in tr.css("td"))
        d = SimpleNamespace(**dict(zip(keys, tds)))

        d.google = _try(lambda: y_n[d.google])
        d.https = _try(lambda: y_n[d.https])
        d.last_checked = _try(lambda: dateparser.parse(d.last_checked))

        acc.append(d)
    return acc


def _try(f, default=None):
    try:
        return f()
    except Exception:
        return default


class Identities(collections.abc.Iterator):
    def __init__(self):
        self._user_agents = UserAgent()
        self._proxies = cycle(
            [p for p in get_proxies() if p.anonymity == "elite proxy"]
        )

    def __next__(self):
        return SimpleNamespace(
            user_agent=self._user_agents.random, **next(self._proxies).__dict__
        )
