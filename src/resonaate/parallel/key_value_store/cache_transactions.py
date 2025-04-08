"""Module implementing transactions that interact with a cache construct."""

# Standard Library Imports
from operator import itemgetter
from time import time_ns
from typing import Any

# Local Imports
from .transaction import Transaction, abbreviateStr


class ValueAlreadySetError(Exception):
    """Error raised by :class:`.InitCache` if cache key already has a value set."""

    def __init__(self, key: str, value: Any):
        """Initialize a :class:`.ValueAlreadySetError`.

        Args:
            key: The key specified by the :class:`.InitCache` transaction.
            value: The value already stored at the specified `key`.
        """
        self.msg = f"Value already set for key '{key}': {abbreviateStr(repr(value))}"

    def __str__(self):
        """Return a string representation of this :class:`.ValueAlreadySetError`."""
        return self.msg


class UninitializedCacheError(Exception):
    """Error raised by :class:`.CacheGrab` if the cache being retrieved from doesn't exist."""

    def __init__(self, cache_name: str):
        """Initialize a :class:`.UninitializedCacheError`.

        Args:
            cache_name: The name of the cache construct specified by the :class:`.CacheGrab`
                transaction.
        """
        self.msg = f"Cache '{cache_name}' has not been initialized."

    def __str__(self):
        """Return a string representation of this :class:`.UninitializedCacheError`."""
        return self.msg


class CacheMissError(Exception):
    """Error raised by :class:`.CacheGrab` if the value being retrieved doesn't exist."""

    def __init__(self, cache_name: str, key: str):
        """Initialize a :class:`.CacheMissError`.

        Args:
            cache_name: The name of the cache construct specified by the :class:`.CacheGrab`
                transaction.
            key: The cache key specified by the :class:`.CacheGrab` transaction.
        """
        self.msg = f"Cache '{cache_name}' does not have a populated value for key '{key}'"

    def __str__(self):
        """Return a string representation of this :class:`.CacheMissError`."""
        return self.msg


class Cache:
    """Encapsulation of the cache construct."""

    def __init__(self, cache_name: str, max_size: int = 128):
        """Initialize a :class:`.Cache` instance.

        Args:
            cache_name: Name of cache to initialize.
            max_size: Maximum number of values that can be stored in this cache before least
                recently used values are purged.
        """
        self.name = cache_name
        self.max_size = max_size
        self._contents: dict = {}
        self._last_accessed: dict[Any, int] = {}

    def getRecord(self, record_name: str) -> Any:
        """Retrieve a record from this cache.

        Args:
            record_name: Unique identifier for the record being retrieved.

        Returns:
            The value of the record being retrieved.

        Raises:
            CacheMissError: If the record does not exist in this cache.
        """
        try:
            record = self._contents[record_name]
        except KeyError as err:
            raise CacheMissError(self.name, record_name) from err
        self._last_accessed[record_name] = time_ns()
        return record

    def putRecord(self, record_name: str, record_value: Any):
        """Store a record in this cache.

        Args:
            record_name: Unique identifier for the record being stored.
            record_value: Value of record being stored.
        """
        self._contents[record_name] = record_value
        self._last_accessed[record_name] = time_ns()

        if len(self._contents) > self.max_size:
            lru_list = sorted(self._last_accessed.items(), key=itemgetter(1))
            lru_key = lru_list[0][0]
            del self._contents[lru_key]
            del self._last_accessed[lru_key]


class InitCache(Transaction):
    """Transaction encapsulating the initialization of a cache construct."""

    def __init__(self, cache_name: str, clear_existing: bool = False, max_size: int = 128):
        """Initialize a :class:`.InitCache` transaction.

        Args:
            cache_name: Name of cache to initialize.
            clear_existing: Flag indicating whether to clear an existing cache. Default is
                ``False``, resulting in an error being raised if a cache already exists for
                `cache_name`.
            max_size: Maximum number of values that can be stored in this cache before least
                recently used values are purged.
        """
        super().__init__(cache_name)
        self.cache_name = cache_name
        self.clear_existing = clear_existing
        self.max_size = max_size

    def transact(self, key_value_store: dict):
        """Instantiate a :class:`.Cache` object at :attr:`.cache_name` in `key_value_store`.

        Args:
            key_value_store: The dictionary object being transacted on.

        See Also:
            :meth:`.KeyValueStore.initCache()`.
        """
        if (value := key_value_store.get(self.cache_name)) is not None and not self.clear_existing:
            self.error = ValueAlreadySetError(self.cache_name, value)
            return

        key_value_store[self.cache_name] = Cache(self.cache_name, max_size=self.max_size)

        self.response_payload = {
            "cache_name": self.cache_name,
            "clear_existing": self.clear_existing,
            "max_size": self.max_size,
        }


def getCache(key_value_store: dict, cache_name: str) -> Cache:
    """Return the cache stored at `cache_name` in `key_value_store`, if it has been initialized.

    Args:
        key_value_store: The key value store dictionary.
        cache_name: Name of the cache to retrieve.

    Returns:
        Cache stored at `cache_name` in `key_value_store`, if it has been initialized.

    Raises:
        UninitializedCacheError: If the value at `cache_name` in `key_value_store` has not been
            initialized as a :class:`.Cache` object.
    """
    cache: Cache = key_value_store.get(cache_name)
    if cache is None or not isinstance(cache, Cache):
        raise UninitializedCacheError(cache_name)
    # else:
    return cache


class CachePut(Transaction):
    """Transaction encapsulating storing a record in a cache construct."""

    def __init__(self, cache_name: str, record_name: str, record_value: Any):
        """Initialize a :class:`.CachePut` transaction.

        Args:
            cache_name: Name of cache to put the record into.
            record_name: Unique identifier for specified record.
            record_value: Value being put into the specified cache.
        """
        super().__init__(cache_name)
        self.cache_name = cache_name
        self.record_name = record_name
        self.record_value = record_value

    def transact(self, key_value_store: dict):
        """Put a value in the specified cache at the specified :attr:`.record_name`.

        Args:
            key_value_store: Dictionary object being transacted upon.

        See Also:
            :meth:`.KeyValueStore.cachePut()`.
        """
        try:
            cache = getCache(key_value_store, self.cache_name)
        except UninitializedCacheError as err:
            self.error = err

        if self.error is None:
            cache.putRecord(self.record_name, self.record_value)

            self.response_payload = {
                "cache_name": self.cache_name,
                "record_name": self.record_name,
                "record_value": self.record_value,
            }


class CacheGrab(Transaction):
    """Transaction encapsulating retrieving a record from a cache construct."""

    def __init__(self, cache_name: str, record_name: str):
        """Initialize a :class:`.CacheGrab` transaction.

        Args:
            cache_name: Name of cache to grab the specified record from.
            record_name: Unique identifier of record to retrieve.
        """
        super().__init__(cache_name)
        self.cache_name = cache_name
        self.record_name = record_name

    def transact(self, key_value_store: dict):
        """Attempt to retrieve the specified record from the specified cache.

        Args:
            key_value_store: Dictionary object being transacted upon.

        See Also:
            :meth:`.KeyValueStore.cacheGrab()`.
        """
        try:
            cache = getCache(key_value_store, self.cache_name)
        except UninitializedCacheError as err:
            self.error = err

        if self.error is None:
            try:
                self.response_payload = cache.getRecord(self.record_name)
            except CacheMissError as miss:
                self.error = miss
