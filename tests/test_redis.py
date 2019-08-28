import pytest
import redis
import roax.redis
import roax.schema as s

from roax.resource import Conflict, NotFound
from time import sleep
from uuid import uuid4


_schema = s.dict(
    {
        "id": s.uuid(),
        "str": s.str(),
        "dict": s.dict({"a": s.int()}),
        "list": s.list(s.int()),
        "set": s.set(s.str()),
        "int": s.int(),
        "float": s.float(),
        "bool": s.bool(),
        "bytes": s.bytes(),
        "date": s.date(),
        "datetime": s.datetime(),
    },
    required={"str"},
)


@pytest.fixture(scope="module")
def resource():
    pool = redis.ConnectionPool()
    connection = redis.Redis(connection_pool=pool)
    connection.flushdb()
    resource = roax.redis.RedisResource(
        connection_pool=pool, schema=_schema, id_schema=_schema.properties["id"]
    )
    yield resource
    connection.flushdb()


def test_create_conflict(resource):
    id = uuid4()
    resource.create(id, {"id": id, "str": "bar"})
    with pytest.raises(Conflict):
        resource.create(id, {"id": id, "str": "baz"})


def test_read(resource):
    id = uuid4()
    value = {
        "id": id,
        "str": "string",
        "dict": {"a": 1},
        "list": [1, 2, 3],
        "set": {"foo", "bar"},
        "int": 1,
        "float": 2.3,
        "bool": True,
        "bytes": b"12345",
        "date": s.date().str_decode("2019-01-01"),
        "datetime": s.datetime().str_decode("2019-01-01T01:01:01Z"),
    }
    response = resource.create(id, value)
    assert response["id"] == id
    assert resource.read(id) == value


def test_read_notfound(resource):
    id = uuid4()
    with pytest.raises(NotFound):
        resource.read(id)


def test_update(resource):
    id = uuid4()
    value = {"id": id, "str": "bar"}
    resource.create(id, value)
    value = {"id": id, "str": "qux"}
    resource.update(id, value)
    assert resource.read(id) == value


def test_update_notfound(resource):
    id = uuid4()
    value = {"id": id, "str": "bar"}
    with pytest.raises(NotFound):
        resource.update(id, value)


def test_delete_notfound(resource):
    id = uuid4()
    with pytest.raises(NotFound):
        resource.delete(id)


def test_ttl():
    xr = roax.redis.RedisResource(
        connection_pool=redis.ConnectionPool(),
        schema=_schema,
        id_schema=_schema.properties["id"],
        ttl=0.001,
    )
    id = uuid4()
    value = {"id": id, "str": "bar"}
    xr.create(id, value)
    xr.read(id)
    sleep(0.002)
    with pytest.raises(NotFound):
        read = xr.read(id)
