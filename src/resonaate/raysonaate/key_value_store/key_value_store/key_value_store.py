from __future__ import annotations
# Standard Library Imports
from contextlib import contextmanager
from multiprocessing import Process
from os import getpid, remove
from threading import Lock
from typing import Any
from warnings import warn
# Third Party Imports
import zmq
# Package Imports
from ..config import Config
from ..logging import getLogger
from ..endpoints import EndpointSpecification
from .append_transaction import AppendTransaction
from .cache_transactions import InitCache, CachePut, CacheGrab
from .dump_transaction import DumpTransaction
from .get_transaction import GetTransaction
from .job_status_transaction import PipelineQueuedTransaction, PipelineDelegatedTransaction, PipelineProcessedTransaction, PipelineReturnedTransaction
from .flush_transaction import FlushTransaction
from .ping_transaction import PingTransaction
from .pop_transaction import PopTransaction
from .set_transaction import SetTransaction
from .shutdown_transaction import ShutdownTransaction
from .transaction import Transaction


class TransactionTimeout(Exception):
    """Exception raised when a :class:`.Transaction` times out waiting for a response from the server."""

    def __init__(self, transaction):
        err = f"Transaction timed out: {transaction}"
        super().__init__(err)


class ServerExistsError(Exception):
    """Exception raised when :meth:`._Server.startServerProcess()` is called when a server has already been started."""

    def __init__(self, instance_id):
        err = f"Server for instance {instance_id} already exists"
        super().__init__(err)


class _Server:
    """Encapsulates the server for the key value store."""

    _LOCK_FILE_NAME_FORMAT = ".strmbrkr-kvs-{}.lock"

    @classmethod
    def startServerProcess(cls):
        """Start the :class:`._Server` in a ``multiprocessing.Process``.

        Raises:
            ServerExistsError: If the server for the specified `instance_id` has already been started.
        """
        try:
            _fd = open(cls._LOCK_FILE_NAME_FORMAT.format(Config.socket.instance_id), 'x')
        except FileExistsError:
            raise ServerExistsError(Config.socket.instance_id)
        else:
            _fd.close()

        server_process = Process(
            target=_Server.startServer,
            name="key_value_store_server",
            daemon=True
        )
        server_process.start()

    @classmethod
    def startServer(cls):
        """Initialize the server and start handling messages.

        Args:
            instance_id (str): Unique identifier of the API instance starting this :class:`._Server`.

        Note:
            This function is intended to be called inside the process that the server will run in.
        """
        server = cls()
        server.startHandling()

    def __init__(self):
        """Initialize the server infrastructure."""
        self._logger = getLogger()

        self._zmq_context = zmq.Context.instance()
        self._socket = self._zmq_context.socket(zmq.REP)
        self._socket.bind(EndpointSpecification.getKeyValueStore(EndpointSpecification.Connection.BIND))

        self._key_value_store = dict()

        self._logger.info("Initialized server...")

    def startHandling(self):
        """Start handling requests received from clients."""
        while not self._key_value_store.get(ShutdownTransaction.SERVER_SHUTDOWN_KEY):
            transaction = self._socket.recv_pyobj()

            self._logger.debug("Server received request: %s", repr(transaction))
            transaction.transact(self._key_value_store)

            self._socket.send_pyobj(transaction)
        remove(self._LOCK_FILE_NAME_FORMAT.format(Config.socket.instance_id))
        self._socket.close()
        self._logger.info("Server exiting.")


class _Client:
    """Encapsulates the client socket and transaction submission procedures."""

    SOCKET_TIMEOUT = Config.key_value_store.client_socket_timeout
    """int: Corresponds to ZMQ_SNDTIMEO: Maximum time before a send operation returns with EAGAIN"""

    SEND_ATTEMPTS = Config.key_value_store.client_socket_attempts
    """int: Number of attempts the client will make to connect with the server."""

    def __init__(self, ):
        self._ignore_transact_exc = tuple()

        self._lock = Lock()
        self._socket = zmq.Context.instance().socket(zmq.REQ)
        self._socket.immediate = True  # ZMQ_IMMEDIATE: Queue messages only to completed connections
        self._socket.sndtimeo = self.SOCKET_TIMEOUT
        self._socket.connect(EndpointSpecification.getKeyValueStore(EndpointSpecification.Connection.CONNECT))

    @contextmanager
    def getSocket(self):
        with self._lock:
            yield self._socket

    def setIgnoreTransactExc(self, ignore: tuple):
        """Update how to handle :class:`.Transaction` exceptions.

        Args:
            ignore (tuple[BaseException]): A tuple of :class:`.Transaction`-thrown exceptions to ignore.
        """
        for exc in ignore:
            if not issubclass(exc, BaseException):
                err = f"Ignored transaction exceptions must inherit from BaseException: {exc}"
                raise TypeError(err)
        self._ignore_transact_exc = ignore

    def submitTransaction(self, transaction: Transaction, ignore_transact_exc: list = None):
        """Submit a :class:`.Transaction` object to the server to be executed.

        Note:
            If a :class:`.ShutdownTransaction` times out, rather than throwing an exception, this method will just warn the
            user.

        Args:
            transaction (Transaction): :class:`.Transaction` object to be executed.
            send_attempts (int): Number of times for the client to try to connect to the server.
            ignore_transact_exc (list, optional): List of ``Exception`` types thrown by the `transaction` that will be
                turned into warnings.

        Returns:
            Any: Result of the :class:`.Transaction` being executed.

        Raises:
            zmq.Again: If the socket can't send the transaction to the server before :attr:`.SOCKET_TIMEOUT`.
            TransactionTimeout: If a response isn't received from the server before :attr:`.SOCKET_TIMEOUT`.
        """
        with self.getSocket() as socket:
            socket.send_pyobj(transaction)

            if socket.poll(self.SOCKET_TIMEOUT):
                transaction = socket.recv_pyobj()
            else:
                exc = TransactionTimeout(transaction)
                if isinstance(transaction, ShutdownTransaction):
                    # [XXX]: Sometimes the server doesn't successfully send the response to the `ShutdownTransaction` before
                    #        exiting. Not sure why this is, but shouldn't be problematic so just warn user instead of hanging.
                    warn(repr(exc))
                else:
                    raise exc

        if ignore_transact_exc is None:
            ignore_transact_exc = self._ignore_transact_exc
        try:
            response = transaction.getResponse()
        except ignore_transact_exc as ignored:
            warn(repr(ignored))
            response = {"error": ignored}
        return response


class KeyValueStore:
    """Client and server operations for a process-safe key-value store."""

    _client_map = {}
    """dict: Keys are process IDs and values are :class:`._Client` instances to use in the corresponding processes."""

    @classmethod
    def _checkServer(cls):
        """Make sure the server is responding to requests in a reasonable amount of time.

        Raises:
            zmq.Again: If the server seems to exist but can't be successfully pinged.
        """
        try:
            _Server.startServerProcess()
        except ServerExistsError:
            pass

        cls.pingServer()

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
            cls._checkServer()
        return _client

    @classmethod
    def setIgnoreTransactExc(cls, ignore: tuple):
        """Update how to handle :class:`.Transaction` exceptions.

        Args:
            ignore (tuple[BaseException]): A tuple of :class:`.Transaction`-thrown exceptions to ignore.
        """
        cls.getClient().setIgnoreTransactExc(ignore)

    @classmethod
    def pingServer(cls, send_attempts: int = 3):
        """Ping the server to test connectivity.

        Args:
            send_attempts (int): Number of times to try to connect to the server.

        Returns:
            dict: Ping information based on the response from the server.

        Raises:
            zmq.Again: If a connection can't be successfully established with the server.
        """
        client = cls.getClient()
        try_again = True
        while try_again:
            try:
                response = client.submitTransaction(PingTransaction())
            except zmq.Again as eagain:
                send_attempts -= 1
                if send_attempts < 1:
                    raise eagain
                continue
            else:
                try_again = False
        return response

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
        return cls.submitTransaction(SetTransaction(key, request_payload = value))

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
        return cls.submitTransaction(AppendTransaction(key, request_payload = value))

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
        return cls.submitTransaction(PopTransaction(key, request_payload = index))

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
    def updatePipelineQueued(cls, job_id: int):
        """Submit a pipeline status update indicating that a job has been queued.

        Args:
            job_id (int): Unique identifier for the job corresponding to the status being updated.

        Returns:
            dict: The current status report for the specified job.
        """
        return cls.submitTransaction(PipelineQueuedTransaction(job_id))

    @classmethod
    def updatePipelineDelegated(cls, job_id: int):
        """Submit a pipeline status update indicating that a job has been delegated to a worker.

        Args:
            job_id (int): Unique identifier for the job corresponding to the status being updated.

        Returns:
            dict: The current status report for the specified job.
        """
        return cls.submitTransaction(PipelineDelegatedTransaction(job_id))

    @classmethod
    def updatePipelineProcessed(cls, job_id: int):
        """Submit a pipeline status update indicating that a job has been processed by a worker.

        Args:
            job_id (int): Unique identifier for the job corresponding to the status being updated.

        Returns:
            dict: The current status report for the specified job.
        """
        return cls.submitTransaction(PipelineProcessedTransaction(job_id))

    @classmethod
    def updatePipelineReturned(cls, job_id: int):
        """Submit a pipeline status update indicating that a job has been returned to the :class:`.QueueManager`.

        Args:
            job_id (int): Unique identifier for the job corresponding to the status being updated.

        Returns:
            dict: The current status report for the specified job.
        """
        return cls.submitTransaction(PipelineReturnedTransaction(job_id))

    @classmethod
    def dump(cls):
        """Dump the key value store's contents to a file."""
        return cls.submitTransaction(DumpTransaction())

    @classmethod
    def flush(cls):
        """Flush the key value store's contents."""
        return cls.submitTransaction(FlushTransaction())

    @classmethod
    def stopServerProcess(cls):
        """Send shutdown request to the server.

        Returns:
            bool: ``True`` if shutdown request was successful.
        """
        return cls.submitTransaction(ShutdownTransaction())
