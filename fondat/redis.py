"""Fondat module for Redis."""

from fondat.codec import BinaryCodec
from fondat.error import NotFoundError
from fondat.pagination import Page
from fondat.resource import operation, resource
from redis.asyncio import Redis
from typing import Any, Generic, Optional, TypeVar


KT = TypeVar("KT")
VT = TypeVar("VT")


@resource
class RedisResource(Generic[KT, VT]):
    """
    Redis database resource.

    • redis: Redis connection or connection pool
    • key_type: type of key to identify value
    • value_type: type of value to store
    • expire: expire time for each value in seconds
    """

    def __init__(
        self,
        redis: Redis,
        key_type: Any,
        value_type: Any,
        expire: int | float | None = None,
    ):
        self.redis = redis
        self.key_codec = BinaryCodec.get(key_type)
        self.value_type = value_type
        self.expire = expire

    @operation
    async def get(self, limit: Optional[int] = None, cursor: Optional[bytes] = None) -> Page[KT]:
        """Return paginated list of keys."""
        kwargs = {"cursor": cursor or b"0"}
        if limit and limit > 0:
            kwargs["count"] = limit
        cursor, keys = await self.redis.scan(**kwargs)
        return Page(
            items=[self.key_codec.decode(key) for key in keys],
            cursor=str(cursor).encode() if cursor else None,
        )

    def __getitem__(self, key: KT) -> "ValueResource":
        """Return value inner resource."""
        return ValueResource(
            self.redis, self.key_codec.encode(key), self.value_type, self.expire
        )


@resource
class ValueResource(Generic[VT]):
    """
    Redis value resource.

    • redis: Redis connection or connection pool
    • key: value key
    • type: type of value to store
    • expire: expire time for value in seconds
    """

    def __init__(
        self,
        redis: Redis,
        key: bytes,
        type: Any,
        expire: int | float | None = None,
    ):
        self.redis = redis
        self.key = key
        self.codec = BinaryCodec.get(type)
        self.expire = expire

    @operation
    async def get(self) -> VT:
        """Get value."""
        value = await self.redis.get(name=self.key)
        if value is None:
            raise NotFoundError
        return self.codec.decode(value)

    @operation
    async def put(self, value: VT) -> None:
        """Set value."""
        await self.redis.set(
            name=self.key,
            value=self.codec.encode(value),
            px=int(self.expire * 1000) if self.expire else None,
        )

    @operation
    async def delete(self) -> None:
        """Delete value."""
        if not await self.redis.delete(self.key):
            raise NotFoundError
