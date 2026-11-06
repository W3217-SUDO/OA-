"""与账号无关的下拉选项：同一进程内短时间复用，省去每次打开页面都重读。

只放响应不依赖当前账号的接口（鉴权仍由接口依赖每次执行）。选项变化最多延迟 ttl 秒。
"""
import asyncio
from copy import deepcopy
from time import monotonic

_entries = {}
_locks = {}


async def cached_options(name, ttl, compute):
    now = monotonic()
    entry = _entries.get(name)
    if entry and now < entry[0]:
        return deepcopy(entry[1])
    lock = _locks.setdefault(name, asyncio.Lock())
    async with lock:
        entry = _entries.get(name)
        if entry and monotonic() < entry[0]:
            return deepcopy(entry[1])
        value = await compute()
        _entries[name] = (monotonic() + ttl, value)
        return deepcopy(value)


def clear_options_cache():
    _entries.clear()
    _locks.clear()
