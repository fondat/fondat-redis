import pytest
import aioredis
import asyncio
import fondat.redis

from dataclasses import dataclass, make_dataclass
from datetime import date, datetime
from fondat.error import NotFoundError
from fondat.paging import paginate
from typing import Optional, TypedDict
from uuid import UUID


pytestmark = pytest.mark.asyncio


@dataclass
class DC:
    id: UUID
    str_: Optional[str]
    dict_: Optional[TypedDict("TD", {"a": int})]
    list_: Optional[list[int]]
    set_: Optional[set[str]]
    int_: Optional[int]
    float_: Optional[float]
    bool_: Optional[bool]
    bytes_: Optional[bytes]
    date_: Optional[date]
    datetime_: Optional[datetime]


@pytest.fixture(scope="function")
async def redis():
    p = await aioredis.create_redis_pool("redis://localhost")
    await p.flushdb()
    try:
        yield p
    finally:
        p.close()
        await p.wait_closed()


@pytest.fixture(scope="function")
async def resource(redis):
    return fondat.redis.redis_resource(redis, UUID, DC)


async def test_crud(resource):
    id = UUID("7af8410d-ffa3-4598-bac8-9ac0e488c9df")
    value = DC(
        id=UUID("7af8410d-ffa3-4598-bac8-9ac0e488c9df"),
        str_="string",
        dict_={"a": 1},
        list_=[1, 2, 3],
        set_={"foo", "bar"},
        int_=1,
        float_=2.3,
        bool_=True,
        bytes_=b"12345",
        date_=date.fromisoformat("2019-01-01"),
        datetime_=datetime.fromisoformat("2019-01-01T01:01:01+00:00"),
    )
    r = resource[id]
    await r.put(value)
    assert await r.get() == value
    value.dict_ = {"a": 2}
    value.list_ = [2, 3, 4]
    value.set_ = None
    value.int_ = 2
    value.float_ = 1.0
    value.bool_ = False
    value.bytes_ = None
    value.date_ = None
    value.datetime_ = None
    await r.put(value)
    assert await r.get() == value
    await r.delete()
    with pytest.raises(NotFoundError):
        await r.delete()
    with pytest.raises(NotFoundError):
        await r.get()


async def test_expire(redis):
    DC = make_dataclass("DC", (("string", str),))
    resource = fondat.redis.redis_resource(redis, str, DC, expire=0.01)
    r = resource["a"]
    value = DC("foo")
    await r.put(value)
    await r.get() == value
    await asyncio.sleep(0.01)
    with pytest.raises(NotFoundError):
        await r.get()
    with pytest.raises(NotFoundError):
        await r.delete()


async def test_pagination(redis):
    resource = fondat.redis.redis_resource(redis, str, str)
    count = 1000
    for n in range(0, count):
        await resource[f"{n:04d}"].put("value")
    assert len([v async for v in paginate(resource.get)]) == count
