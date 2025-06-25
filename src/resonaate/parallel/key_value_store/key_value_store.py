"""Define the Ray-implemented Key Value Store construct."""

from __future__ import annotations

# Standard Library Imports
from os import getpid
from typing import TYPE_CHECKING, Any, ClassVar

# Third Party Imports
import ray

# Local Imports
# Package Imports
from .append_transaction import AppendTransaction
from .cache_transactions import CacheGrab, CachePut, InitCache
from .dump_transaction import DumpTransaction
from .flush_transaction import FlushTransaction
from .get_transaction import GetTransaction
from .pop_transaction import PopTransaction
from .set_transaction import SetTransaction

if TYPE_CHECKING:
    # Local Imports
    from .transaction import Transaction


@ray.remote
class _KVSActor:
    """Encapsulates the server for the key value store."""

    def __init__(self):
        """Initialize the server infrastructure."""
        self._key_value_store = {}

    def executeTransaction(self, transaction: Transaction):
        """Execute the transaction encapsulated by `transaction`.

        Args:
            transaction: The transaction to be executed.
        """
        transaction.transact(self._key_value_store)
        return transaction


class _Client:
    """Encapsulates Ray specific code for interacting with the :class:`._KVSActor`."""

    ACTOR_NAME: str = "resonaate-kvs-actor"

    def __init__(
        self,
        actor_name: str | None = None,
    ):
        """Initialize a handle to a :class:`._KvsActor`.

        Args:
            actor_name: The name of the Ray actor that will interface with the :class:`._KVSActor`.
        """
        if actor_name is None:
            actor_name = self.ACTOR_NAME
        self._handle = _KVSActor.options(
            name=actor_name,
            get_if_exists=True,
        ).remote()

    def submitTransaction(self, transaction: Transaction):
        """Submit a :class:`.Transaction` object to the :class:`._KVSActor` to be executed.

        Args:
            transaction (Transaction): :class:`.Transaction` object to be executed.

        Returns:
            Any: The :class:`.Transaction` after being processed by the :class:`._KVSActor`.
        """
        task_handle = self._handle.executeTransaction.remote(transaction)
        result = ray.get(task_handle)
        return result.getResponse()


class KeyValueStore:
    """Client and server operations for a process-safe key-value store."""

    _client_map: ClassVar = {}
    """dict: Keys are process IDs and values are :class:`._Client` instances to use in the corresponding processes."""

    @classmethod
    def getClient(cls):
        """Retrieve the :class:`._Client` allocated for the current process.

        Returns:
            _Client: The :class:`._Client` allocated for the current process.
        """
        curr_pid = getpid()
        _client = cls._client_map.get(curr_pid)
        if _client is None:
            _client = _Client()
            cls._client_map[curr_pid] = _client
        return _client

    @classmethod
    def submitTransaction(cls, transaction: Transaction):
        """Submit a :class:`.Transaction` to be executed.

        Before `transaction` is submitted, the server is confirmed to be up.

        Args:
            transaction (Transaction): The transaction to be executed.

        Returns:
            Any: The results of the :meth:`transaction.getResponse()` call.
        """
        return cls.getClient().submitTransaction(transaction)

    @classmethod
    def getValue(cls, key: str):
        """Get the value stored at specified `key`.

        Args:
            key (str): Key of value being retrieved.

        Returns:
            ``Any``: Value stored at specified `key`. If the value is not set, this function will return ``None``.
        """
        return cls.submitTransaction(GetTransaction(key))

    @classmethod
    def setValue(cls, key: str, value):
        """Set the value stored at specified `key` to `value`.

        Args:
            key (str): Key of value being set.
            value (``Any``): Value being set.

        Returns:
            ``Any``: Value stored at specified `key` after setting to `value`.
        """
        return cls.submitTransaction(SetTransaction(key, request_payload=value))

    @classmethod
    def appendValue(cls, key: str, value):
        """Append `value` to the value stored at specified `key`.

        If no value is currently stored at `key`, then set the value to a list with one element of `value`.

        Args:
            key (str): Key of value being appended to.
            value (``Any``): Value being appended.

        Returns:
            ``Any``: Value stored at specified `key` after appending `value`.

        Raises:
            TypeError: Raised if there is a value currently stored at `key`, but it is not a mutable sequence.
        """
        return cls.submitTransaction(AppendTransaction(key, request_payload=value))

    @classmethod
    def popValue(cls, key: str, index: int):
        """Remove and return the first element of the current value of a key.

        Args:
            key (str): Key of value being retrieved from.
            index (int): Index to pop off of an existing list stored at specified `key`.

        Returns:
            ``Any``: Value stored at specified `key`. If the value is not set, this function will return ``None``.

        Raises:
            TypeError: Raised if there is the value currently stored at `key`, but it is not a mutable sequence.
        """
        return cls.submitTransaction(PopTransaction(key, index=index))

    @classmethod
    def initCache(cls, cache_name: str, clear_existing: bool = False, max_size: int = 128) -> dict:
        """Initialize the cache specified by the arguments.

        Args:
            cache_name: Name of the cache to be initialized.
            clear_existing: Flag indicating whether to clear an existing cache. Default is
                ``False``, resulting in an error being raised if a cache already exists for
                `cache_name`.
            max_size: Maximum number of values that can be stored in this cache before least
                recently used values are purged.

        Returns:
            dict: Dictionary that echoes the provided arguments.

        Raises:
            ValueAlreadySet: If `clear_existing` is ``False`` and a value already exists at the key
                specified by `cache_name`.
        """
        return cls.submitTransaction(InitCache(cache_name, clear_existing, max_size))

    @classmethod
    def cachePut(cls, cache_name: str, record_name: str, record_value: Any) -> dict:
        """Store a record in the specified cache.

        Args:
            cache_name: Name of cache to put the record into.
            record_name: Unique identifier for specified record.
            record_value: Value being put into the specified cache.

        Returns:
            Dictionary that echoes the provided arguments.

        Raises:
            UninitializedCache: If the cache specified by `cache_name` has not been initialized.
        """
        return cls.submitTransaction(CachePut(cache_name, record_name, record_value))

    @classmethod
    def cacheGrab(cls, cache_name: str, record_name: str) -> Any:
        """Attempt to retrieve a specified record from a specified cache.

        Args:
            cache_name: Name of cache to grab the specified record from.
            record_name: Unique identifier of record to retrieve.

        Returns:
            The record value mapped to `record_name` in the cache.

        Raises:
            UninitializedCache: If the cache specified by `cache_name` has not been initialized.
            CacheMiss: If the specified `record_name` is not mapped to a value in the cache.
        """
        return cls.submitTransaction(CacheGrab(cache_name, record_name))

    @classmethod
    def dump(cls, dump_filename: str | None = None):
        """Dump the key value store's contents to a file.

        Args:
            dump_filename: Path to file to dump key value store contents to.
        """
        return cls.submitTransaction(DumpTransaction(dump_filename=dump_filename))

    @classmethod
    def flush(cls):
        """Flush the key value store's contents."""
        return cls.submitTransaction(FlushTransaction())
