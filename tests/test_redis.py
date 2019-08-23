import pytest
import redis
import roax.schema as s

from roax.redis import RedisResource
from roax.resource import Conflict, NotFound
from time import sleep
from uuid import uuid4


_schema = s.dict(
    properties={"id": s.uuid(), "foo": s.str(), "bar": s.int()}, required={"foo"}
)


@pytest.fixture(scope="module")
def redis_resource():
    pool = redis.ConnectionPool()
    connection = redis.Redis(connection_pool=pool)
    connection.flushdb()
    resource = RedisResource(
        connection_pool=pool, schema=_schema, id_schema=_schema.properties["id"]
    )
    yield resource
    connection.flushdb()


def test_create_conflict(redis_resource):
    id = uuid4()
    redis_resource.create(id, {"id": id, "foo": "bar"})
    with pytest.raises(Conflict):
        redis_resource.create(id, {"id": id, "foo": "baz"})


def test_read(redis_resource):
    id = uuid4()
    value = {"id": id, "foo": "bar"}
    response = redis_resource.create(id, value)
    assert response["id"] == id
    assert redis_resource.read(id) == value


def test_read_notfound(redis_resource):
    id = uuid4()
    with pytest.raises(NotFound):
        redis_resource.read(id)


def test_update(redis_resource):
    id = uuid4()
    value = {"id": id, "foo": "bar"}
    redis_resource.create(id, value)
    value = {"id": id, "foo": "qux"}
    redis_resource.update(id, value)
    assert redis_resource.read(id) == value


def test_update_notfound(redis_resource):
    id = uuid4()
    value = {"id": id, "foo": "bar"}
    with pytest.raises(NotFound):
        redis_resource.update(id, value)


def test_delete_notfound(redis_resource):
    id = uuid4()
    with pytest.raises(NotFound):
        redis_resource.delete(id)


def test_ttl():
    xr = RedisResource(
        connection_pool=redis.ConnectionPool(),
        schema=_schema,
        id_schema=_schema.properties["id"],
        ttl=0.001,
    )
    id = uuid4()
    value = {"id": id, "foo": "bar"}
    xr.create(id, value)
    xr.read(id)
    sleep(0.002)
    with pytest.raises(NotFound):
        read = xr.read(id)
