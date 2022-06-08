"""Control module for managing the task queues."""
# Standard Imports
from pickle import dumps, loads
from queue import Queue
from threading import Thread
from time import sleep
from traceback import format_exc
from uuid import uuid4
# Third Party Imports
# RESONAATE Imports
from . import TASK_QUEUE_LIST, TASK_QUEUE_NAME_PREFIX, PROCESSED_QUEUE_NAME_PREFIX
from . import getRedisConnection, REDIS_QUEUE_LOGGER
from .task import Task
from ..common.exceptions import TaskTimeoutError


class QueueManager:
    """Class for managing queuing of new tasks and handling of completed tasks."""

    _BLOCK_INTERVAL = 1
    """float: How many seconds to wait between checking for task completion while blocking."""

    def __init__(self, processed_callback=None, logger=None):
        """Instantiate a :class:`.QueueManager` object.

        Args:
            processed_callback (callable, optional): Callback to execute each time a processed
                task is returned by a worker.
            logger (logging.Logger, optional): Custom logging instance for :class:`.QueueManager`
                to use, instead of :attr:`.REDIS_QUEUE_LOGGER` .
        """
        if logger is not None:
            self._logger = logger
        else:
            self._logger = REDIS_QUEUE_LOGGER

        self._redis_conn = getRedisConnection()

        # Determine names of task/processed task queues and register the name with Redis
        self._queue_id = str(uuid4())
        self._task_queue_name = TASK_QUEUE_NAME_PREFIX + self._queue_id
        self._processed_queue_name = PROCESSED_QUEUE_NAME_PREFIX + self._queue_id
        self._redis_conn.rpush(TASK_QUEUE_LIST, self._task_queue_name)
        self._logger.info("Registered task queue: {0}".format(self._task_queue_name))

        self._queued_task_ids = set()

        self._results = Queue()
        self._callback = processed_callback

        self._task_handler_exception = None
        self._task_handler_traceback = None

        self._processed_task_handler = Thread(target=self._handleProcessedTasks, daemon=True)
        self._processed_task_handler.start()

    def queueTasks(self, *args):
        """Add tasks to the queue.

        Args:
            *args: Variable length list of :class:`.Task` objects to be queued.
        """
        for task in args:
            if not isinstance(task, Task):
                err = "Cannot queue objects of '{0}'".format(type(task))
                raise ValueError(err)
            self._logger.debug("Queuing task {0}".format(task.id))
            serialized = dumps(task)
            self._queued_task_ids.add(task.id)
            self._redis_conn.rpush(self._task_queue_name, serialized)

    def _handleProcessedTasks(self):
        """Handle processed tasks returned from workers.

        This method continuously attempts to pop processed tasks off of a second task queue where
        workers return their results to and handle the results appropriately. This method is
        automatically started in another ``threading.Thread`` during the construction of a
        :class:`.QueueManager` .

        If no ``processed_callback`` is given to this :class:`.QueueManager` 's constructor, then
        handling processed tasks defaults to logging the task's reception and putting it on a
        ``Queue`` . These are retrievable via :meth:`.getResults()` .

        If ``processed_callback`` *is* given to the constructor, then handling will consist of
        calling ``processed_callback`` with the processed :class:`.Task` as its single argument.
        """
        while 1:
            try:
                ret = self._redis_conn.blpop(self._processed_queue_name)
                processed_task = loads(ret[1])

                if self._callback is None:
                    msg = "Task {0.id} returned {0.retval} with status code {0.status}"
                    self._logger.info(msg.format(processed_task))
                    self._results.put(processed_task)
                else:
                    self._callback(processed_task)
                self._queued_task_ids.remove(processed_task.id)

            except Exception as error:  # pylint: disable=broad-except
                self._task_handler_exception = error
                self._task_handler_traceback = format_exc()

    @property
    def queued_tasks_processed(self):
        """bool: Boolean indicating whether all queued tasks have been processed and handled."""
        return len(self._queued_task_ids) == 0

    @property
    def queued_task_ids(self):
        """set: Set of task IDs that have been queued, but not processed."""
        return self._queued_task_ids

    def blockUntilProcessed(self, timeout=None):
        """Block until all queued tasks have been processed and handled.

        Args:
            timeout (float, optional): How long to wait for tasks to be processed and handled.
                Defaults to ``None``, which will wait indefinitely for tasks to process and be
                handled.
        """
        if timeout is not None:
            if timeout < self._BLOCK_INTERVAL:
                interval = timeout
            else:
                interval = self._BLOCK_INTERVAL

            waited = 0.0
            while not self.queued_tasks_processed and waited < timeout:
                sleep(interval)
                waited += interval

                if self._task_handler_exception is not None:
                    self._logger.error(
                        "Error occurred in task handler thread: \n{0}".format(self._task_handler_traceback)
                    )
                    raise self._task_handler_exception

            if not self.queued_tasks_processed:
                raise TaskTimeoutError(
                    "Reached timeout with {0} tasks left to process.".format(len(self._queued_task_ids))
                )

        else:
            while not self.queued_tasks_processed:
                sleep(self._BLOCK_INTERVAL)

                if self._task_handler_exception is not None:
                    self._logger.error(
                        "Error occurred in task handler thread: \n{0}".format(self._task_handler_traceback)
                    )
                    raise self._task_handler_exception

    def getResults(self):
        """Retrieve processed :class:`.Task` s for post-processing.

        Note:
            It is the user's responsibility to utilize :meth:`.blockUntilProcessed()` or
            :attr:`.queued_tasks_processed` to wait for currently queued tasks to complete. Calling
            :meth:`.getResults()`  before all tasks have been processed could result in tasks being
            left on the :attr:`._results` queue, which could lead to errors in subsequent batches
            of processing.
        """
        ret = []
        while not self._results.empty():
            ret.append(self._results.get())

        return ret

    def close(self):
        """Delete task/processed queues and un-register the names from Redis."""
        self._redis_conn.delete(self._task_queue_name)
        self._redis_conn.delete(self._processed_queue_name)
        self._redis_conn.lrem(TASK_QUEUE_LIST, 1, self._task_queue_name)

    def __del__(self):
        """Call :meth:`.close()` when :class:`.QueueManager` goes out of scope."""
        self.close()
