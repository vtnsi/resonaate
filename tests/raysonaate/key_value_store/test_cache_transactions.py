"""Test the functionality of the ``cache_transactions`` module."""

# Third Party Imports
import pytest

# RESONAATE Imports
from resonaate.parallel.key_value_store.cache_transactions import (
    Cache,
    CacheGrab,
    CacheMissError,
    CachePut,
    InitCache,
    UninitializedCacheError,
)

CACHE_NAME = "my_cache"
KEY = "my_key"
VALUE = "my_value"


def test_initCache():
    """Test basic use of :class:`.InitCache`."""
    test_dict = {}
    trans = InitCache(CACHE_NAME)
    trans.transact(test_dict)
    assert isinstance(test_dict[CACHE_NAME], Cache)


def test_duplicateInitCache():
    """Test usage of :class:`.InitCache` when there's an existing value."""
    test_dict = {}
    trans = InitCache(CACHE_NAME)
    trans.transact(test_dict)
    assert isinstance(test_dict[CACHE_NAME], Cache)

    trans.transact(test_dict)
    assert trans.error is not None

    trans = InitCache(CACHE_NAME, clear_existing=True)
    trans.transact(test_dict)
    assert trans.error is None


def test_cachePutGrab():
    """Test basic usage of :class:`.CachePut` and :class:`.CacheGrab`."""
    test_dict = {}
    init_trans = InitCache(CACHE_NAME)
    init_trans.transact(test_dict)
    assert isinstance(test_dict[CACHE_NAME], Cache)

    put_trans = CachePut(CACHE_NAME, KEY, VALUE)
    put_trans.transact(test_dict)
    assert put_trans.error is None
    assert test_dict[CACHE_NAME].getRecord(KEY) == VALUE

    grab_trans = CacheGrab(CACHE_NAME, KEY)
    grab_trans.transact(test_dict)
    assert grab_trans.error is None
    assert grab_trans.response_payload == VALUE


def test_noCachePut():
    """Test use of :class:`.CachePut` if there is no :class:`.Cache`."""
    test_dict = {}
    put_trans = CachePut(CACHE_NAME, KEY, VALUE)
    put_trans.transact(test_dict)
    assert isinstance(put_trans.error, UninitializedCacheError)


def test_noCacheGrab():
    """Test use of :class:`.CacheGrab` if there is no :class:`.Cache`."""
    test_dict = {}
    grab_trans = CacheGrab(CACHE_NAME, KEY)
    grab_trans.transact(test_dict)
    assert isinstance(grab_trans.error, UninitializedCacheError)


def test_cacheMiss():
    """Test use of :class:`.CacheGrab` if there's no value cached."""
    test_dict = {}
    init_trans = InitCache(CACHE_NAME)
    init_trans.transact(test_dict)
    assert isinstance(test_dict[CACHE_NAME], Cache)

    grab_trans = CacheGrab(CACHE_NAME, KEY)
    grab_trans.transact(test_dict)
    assert isinstance(grab_trans.error, CacheMissError)


def test_cacheSize():
    """Make sure :class:`.Cache` objects adhere to their size constraints."""
    cache_size = 16
    cache = Cache(CACHE_NAME, max_size=cache_size)

    for index in range(cache_size * 2):
        cache.putRecord(f"id_{index}", index)

    for index in range(cache_size):
        with pytest.raises(CacheMissError):
            cache.getRecord(f"id_{index}")

        upper_index = cache_size + index
        assert cache.getRecord(f"id_{upper_index}") == upper_index
