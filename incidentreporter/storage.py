from __future__ import annotations

import datetime
import os
from typing import Callable, Union, AsyncGenerator, List, Optional

import aredis


STRINGABLE = Union[str, int, float, bool, bytes]
TIME_TYPE = Union[int, float, datetime.timedelta, datetime.datetime]

SEPERATOR = ':'
_NOT_SET = object()


class GetMixin:
    async def get(self, ref, default=None) -> bytes:
        raise NotImplementedError

    async def get_cast(self, ref, cast: Callable, default=None):
        """Gets a variables and casts it.

        E.g. Use 'bytes.decode' to get a string, 'int' for a integer,
        'float' for a float, etc...
        """
        value = await self.get(ref, default=_NOT_SET)
        if value is _NOT_SET:
            return default
        return cast(value)

    async def get_str(self, ref, default=None) -> str:
        return await self.get_cast(ref, bytes.decode, default=default)

    async def get_int(self, ref, default=None) -> int:
        return await self.get_cast(ref, int, default=default)

    async def get_float(self, ref, default=None) -> float:
        return await self.get_cast(ref, float, default=default)


class Storage(GetMixin):
    __slots__ = ('_redis', '_path')

    def __init__(self, redis: aredis.StrictRedis, path: str = ''):
        self._redis = redis
        self._path = path

    def __truediv__(self, other):
        if not self._path:
            return Storage(self._redis, str(other))
        return Storage(self._redis, self._path + SEPERATOR + str(other))

    def __getitem__(self, item) -> Storage:
        return Storage(
            self._redis,
            SEPERATOR.join(self._path.split(SEPERATOR)[:item])
        )

    def _get_key(self, key: str) -> str:
        if not key:
            return self._path
        if not self._path:
            return key
        return self._path + SEPERATOR + key

    @staticmethod
    def _to_relative_time(time: TIME_TYPE) -> float:
        if isinstance(time, datetime.datetime):
            time = time - datetime.datetime.utcnow()
        if isinstance(time, datetime.timedelta):
            seconds = time.total_seconds()
            return seconds
        return time

    # simple setter/getter/deleter
    async def set(
                self,
                key: str,
                value: STRINGABLE,
                *,
                expires: TIME_TYPE = None,
                only_if_nonexistent: bool = False,
                only_if_exists: bool = False
            ) -> bool:
        kwargs = {}

        if expires is not None:
            expires_in = self._to_relative_time(expires)
            if expires_in > 0:
                # Use px if there are any milliseconds, ex otherwise
                if expires_in % 1:
                    kwargs['px'] = int(expires_in * 1000)
                else:
                    kwargs['ex'] = int(expires_in)

            else:
                # Time in past, key should expire immediately
                # so don't bother setting it
                await self.delete(key)
                return True

        if only_if_exists and only_if_nonexistent:
            raise ValueError('conflicting arguments')

        if only_if_exists:
            kwargs['xx'] = True
        elif only_if_nonexistent:
            kwargs['nx'] = True

        return await self._redis.set(
            self._get_key(key),
            value,
            **kwargs
        )

    async def get(self, key: str, default=None) -> bytes:
        value = await self._redis.get(
            self._get_key(key)
        )
        if value is None:
            return default
        return value

    async def delete(self, key: str, *keys: str):
        return await self._redis.delete(
            self._get_key(key),
            *[self._get_key(x) for x in keys]
        )

    async def exists(self, key: str, *keys: str) -> int:
        return await self._redis.exists(
            self._get_key(key),
            *[self._get_key(x) for x in keys]
        )

    # scan
    async def scan(self, match: str = None,
                   count: int = None) -> AsyncGenerator[str]:
        async for data in self._redis.scan_iter(
                    self._get_key(match) if match else None,
                    count
                ):
            yield data.decode()

    # expire functions
    async def ttl(self, key: str) -> float:
        ttl = await self._redis.pttl(
            self._get_key(key)
        )
        if ttl > 0:
            return ttl / 1000
        return ttl

    async def expire(self, key: str, expires: TIME_TYPE) -> bool:
        expires_in = self._to_relative_time(expires)
        if expires_in <= 0:
            await self.delete(key)
            return True

        if expires_in % 1:
            return await self._redis.pexpire(
                self._get_key(key),
                int(expires_in * 1000)
            )
        return await self._redis.expire(
            self._get_key(key),
            int(expires_in)
        )

    # integer operations
    async def increment(self, key: str) -> int:
        return int(await self._redis.incr(
            self._get_key(key)
        ))

    async def increment_by(self, key: str, amount: int) -> int:
        return int(await self._redis.incrby(
            self._get_key(key),
            amount
        ))

    async def decrement(self, key: str) -> int:
        return int(await self._redis.decr(
            self._get_key(key)
        ))

    async def decrement_by(self, key: str, amount: int) -> int:
        return await self._redis.decrby(
            self._get_key(key),
            amount
        )

    # list / set operators
    async def sort(
                self,
                key: str,
                *get: str,
                by: str = None,
                desc: bool = False,
                alpha: bool = False,
                store: str = None
            ) -> Optional[List[bytes]]:
        return await self._redis.sort(
            self._get_key(key),
            *[self._get_key(x) for x in get],
            by=self._get_key(by) if by else by,
            desc=desc,
            alpha=alpha,
            store=self._get_key(store) if store else store
        )

    def as_dict(self, key: str) -> DictView:
        return DictView(self, key)

    def as_list(self, key: str) -> ListView:
        return ListView(self, key)

    def as_set(self, key: str) -> SetView:
        return SetView(self, key)


class DictView(GetMixin):
    def __init__(self, storage: Storage, key: str):
        self._storage = storage
        self._key = key

    async def get(self, key: str, default=None) -> bytes:
        value = await self._storage._redis.hget(
            self._storage._get_key(self._key),
            key
        )
        if value is None:
            return default
        return value

    async def set(self, key: str, value: STRINGABLE):
        await self._storage._redis.hset(
            self._storage._get_key(self._key),
            key,
            value
        )

    async def update(self, *e, **f):
        # behavior as specified in dict.update.__doc__
        # have to use lowercase f instead of uppercase as in the docstring,
        #   because of PEP-8 >:(
        mapping = {}
        for E in e:
            if hasattr(E, 'keys'):
                for k in E:
                    mapping[k] = E[k]
            else:
                for k, v in E:
                    mapping[k] = v

        for k in f:
            mapping[k] = f[k]

        # aredis does not have support for 'mapping', so I'll have to use
        #   execute_command directly
        # See also: https://github.com/NoneGG/aredis/issues/179

        # await self._storage._redis.hset(
        #     self._storage._get_key(self._key),
        #     mapping=mapping
        # )
        args = []
        for item in mapping.items():
            args.extend(item)
        await self._storage._redis.execute_command(
            'HSET',
            self._storage._get_key(self._key),
            *args
        )

    async def clear(self):
        # there's no special clear command, so just delete it
        await self._storage.delete(self._key)

    async def keys(self):
        return await self._storage._redis.hkeys(
            self._storage._get_key(self._key)
        )

    async def values(self):
        return await self._storage._redis.hvals(
            self._storage._get_key(self._key)
        )

    async def items(self) -> AsyncGenerator[str]:
        cursor = '0'
        while cursor != 0:
            cursor, data = await self._storage._redis.hscan(
                self._storage._get_key(self._key), cursor=cursor
            )
            for item in data:
                yield item, data[item]

    async def copy(self) -> dict:
        dict = {}
        async for key, value in self.items():
            dict[key] = value
        return dict

    async def pop(self, key: str):
        value = await self.get(key)
        await self.del_(key)
        return value

    async def del_(self, key: str):
        return await self._storage._redis.hdel(
            self._storage._get_key(self._key),
            key
        )

    async def contains(self, key: str):
        return await self._storage._redis.hexists(
            self._storage._get_key(self._key),
            key
        )

    async def len(self):
        return await self._storage._redis.hlen(
            self._storage._get_key(self._key)
        )

    async def __aiter__(self):
        return self._storage._redis.hscan_iter(
            self._storage._get_key(self._key)
        )

    __getitem__ = get


class ListView(GetMixin):
    def __init__(self, storage: Storage, key: str):
        self._storage = storage
        self._key = key

    async def get(self, index: int, default=None) -> bytes:
        value = await self._storage._redis.lindex(
            self._storage._get_key(self._key),
            index
        )
        if value is None:
            return default
        return value

    async def set(self, index: int, object: STRINGABLE):
        await self._storage._redis.lset(
            self._storage._get_key(self._key),
            index,
            object
        )

    async def append(self, object: STRINGABLE):
        await self._storage._redis.rpush(
            self._storage._get_key(self._key),
            object
        )

    async def clear(self):
        # there's no special clear command, so just delete it
        await self._storage.delete(self._key)

    async def copy(self):
        copy = []
        async for object in self:
            copy.append(object)
        return copy

    async def count(self, object: STRINGABLE):
        if not isinstance(object, bytes):
            object = str(object).encode()
        total = 0
        async for item in self:
            if item == object:
                total += 1
        return total

    async def extend(self, objects):
        await self._storage._redis.rpush(
            self._storage._get_key(self._key),
            *objects
        )

    async def index(self, object: STRINGABLE, start: int = 0,
                    stop: int = 9223372036854775807):
        if not isinstance(object, bytes):
            object = str(object).encode()
        itemno = 0  # enumerate doesn't work with async-iterators
        async for item in self:
            if item == object and itemno > start:
                return itemno
            itemno += 1
            if itemno >= stop:
                break

    async def pop(self, index: int = -1):
        if index == -1:
            return await self._storage._redis.rpop(
                self._storage._get_key(self._key)
            )
        value = await self.get(index)
        await self.del_(index)
        return value

    async def remove(self, value: STRINGABLE):
        await self._storage._redis.lrem(
            self._storage._get_key(self._key),
            1,
            value
        )

    async def del_(self, index: int):
        # this is not really secure, but should never collide
        value = b'_' + os.urandom(32)
        await self.set(index, value)
        await self.remove(value)

    async def len(self):
        return await self._storage._redis.llen(
            self._storage._get_key(self._key)
        )

    async def __aiter__(self):
        for object in await self._storage._redis.lrange(
                    self._storage._get_key(self._key),
                    0, -1
                ):
            yield object

    __getitem__ = get


class SetView:
    def __init__(self, storage: Storage, key: str):
        self._storage = storage
        self._key = key

    async def add(self, item: STRINGABLE):
        await self._storage._redis.sadd(
            self._storage._get_key(self._key),
            item
        )

    async def clear(self):
        # there's no special clear command, so just delete it
        await self._storage.delete(self._key)

    async def copy(self):
        s = set()
        async for item in self:
            s.add(item)
        return s

    async def extend(self, items):
        await self._storage._redis.sadd(
            self._storage._get_key(self._key),
            *items
        )

    async def pop(self):
        return await self._storage._redis.spop(
            self._storage._get_key(self._key)
        )

    async def remove(self, item: STRINGABLE):
        await self._storage._redis.srem(
            self._storage._get_key(self._key),
            item
        )

    async def contains(self, item: STRINGABLE):
        return await self._storage._redis.sismember(
            self._storage._get_key(self._key),
            item
        )

    async def len(self):
        return await self._storage._redis.scard(
            self._storage._get_key(self._key)
        )

    async def __aiter__(self):
        async for item in self._storage._redis.sscan_iter(
                    self._storage._get_key(self._key)
                ):
            yield item
