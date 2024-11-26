# RESONAATE Imports
from resonaate.agents.agent_cache import NestedGet


def testGoodNestedGet():
    kvs = {"foo": {123: "bar"}}
    
    nested_get = NestedGet(["foo", 123])
    nested_get.transact(kvs)
    assert nested_get.response_payload == "bar"


def testNestedGetTooDeep():
    kvs = {"foo": 123}

    nested_get = NestedGet(["foo", 123])
    nested_get.transact(kvs)
    assert nested_get.error
    print(nested_get.error)


def testNestedGetMiss():
    kvs = {"foo": {123: "bar"}}

    nested_get = NestedGet(["foo", 456])
    nested_get.transact(kvs)
    assert nested_get.response_payload is None
    assert nested_get.error
    print(nested_get.error)
