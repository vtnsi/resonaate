# RESONAATE Imports
from resonaate.agents.agent_cache import NestedGet


def testGoodNestedGet():
    """Validate that nested get works if nested key is set."""
    kvs = {"foo": {123: "bar"}}

    nested_get = NestedGet(["foo", 123])
    nested_get.transact(kvs)
    assert nested_get.response_payload == "bar"


def testNestedGetTooDeep():
    """Validate that nested get fails if outer key doesn't exist."""
    kvs = {"foo": 123}

    nested_get = NestedGet(["foo", 123])
    nested_get.transact(kvs)
    assert nested_get.error
    print(nested_get.error)


def testNestedGetMiss():
    """Validate that nested get fails if inner key doesn't exist."""
    kvs = {"foo": {123: "bar"}}

    nested_get = NestedGet(["foo", 456])
    nested_get.transact(kvs)
    assert nested_get.response_payload is None
    assert nested_get.error
    print(nested_get.error)
