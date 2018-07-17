from .asynctools import agnostic


@agnostic
async def get(*args, session=None, **kwargs):
    if session is None:
        async with aiohttp.ClientSession() as session:
            return await get(*args, session=session, **kwargs)
    async with session.get(*args, **kwargs) as response:
        try:
            response.body = await response.read()
            response.sucess = True
        except Exception as exception:
            response.exception = exception
            response.sucess = False
        return response
