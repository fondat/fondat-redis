"""Fondat module for Redis."""

from aioredis import Redis
from collections.abc import Iterable
from fondat.codec import Binary, get_codec
from fondat.error import NotFoundError
from fondat.pagination import make_page_dataclass
from fondat.resource import resource, operation
from fondat.security import Policy
from typing import Union


def redis_resource(
    redis: Redis,
    key_type: type,
    value_type: type,
    expire: Union[int, float] = 0,
    policies: Iterable[Policy] = None,
):
    """
    Return a new resource that manages values in a Redis server.

    Parameters:
    • redis: Redis connection or connection pool
    • key_type: type of key to identify value
    • value_type: type of value to store
    • expire: expire time for each value in seconds
    • security: security policies to apply to all operations
    """

    key_codec = get_codec(Binary, key_type)
    value_codec = get_codec(Binary, value_type)

    @resource
    class ValueResource:
        """Redis value resource."""

        def __init__(self, key: key_type):
            self.key = key_codec.encode(key)

        @operation(policies=policies)
        async def get(self) -> value_type:
            """Get value."""
            value = await redis.get(self.key)
            if value is None:
                raise NotFoundError
            return value_codec.decode(value)

        @operation(policies=policies)
        async def put(self, value: value_type) -> None:
            """Set value."""
            await redis.set(self.key, value_codec.encode(value), pexpire=int(expire * 1000))

        @operation(policies=policies)
        async def delete(self) -> None:
            """Delete value."""
            if not await redis.delete(self.key):
                raise NotFoundError

    Page = make_page_dataclass("Page", key_type)

    @resource
    class RedisResource:
        """Redis database resource."""

        @operation(policies=policies)
        async def get(self, limit: int = None, cursor: bytes = None) -> Page:
            """Return paginated list of keys."""
            kwargs = {"cursor": cursor or b"0"}
            if limit and limit > 0:
                kwargs["count"] = limit
            cursor, keys = await redis.scan(**kwargs)
            return Page(
                items=[key_codec.decode(key) for key in keys],
                cursor=str(cursor).encode() if cursor else None,
            )

        def __getitem__(self, key: key_type) -> ValueResource:
            """Return value inner resource."""
            return ValueResource(key)

    return RedisResource()
