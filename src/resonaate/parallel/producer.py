"""Control module for managing the job queues."""
# Standard Imports
from pickle import dumps, loads
from queue import Queue
from threading import Thread
from time import sleep
from traceback import format_exc
from uuid import uuid4
# Third Party Imports
# RESONAATE Imports
from . import JOB_QUEUE_LIST, JOB_QUEUE_NAME_PREFIX, PROCESSED_QUEUE_NAME_PREFIX
from . import getRedisConnection, REDIS_QUEUE_LOGGER
from .job import Job
from ..common.exceptions import JobTimeoutError


class QueueManager:
    """Class for managing queuing of new jobs and handling of completed jobs."""

    _BLOCK_INTERVAL = 1
    """float: How many seconds to wait between checking for job completion while blocking."""

    def __init__(self, processed_callback=None, logger=None):
        """Instantiate a :class:`.QueueManager` object.

        Args:
            processed_callback (callable, optional): Callback to execute each time a processed
                job is returned by a worker.
            logger (logging.Logger, optional): Custom logging instance for :class:`.QueueManager`
                to use, instead of :attr:`.REDIS_QUEUE_LOGGER` .
        """
        if logger is not None:
            self._logger = logger
        else:
            self._logger = REDIS_QUEUE_LOGGER

        self._redis_conn = getRedisConnection()

        # Determine names of job/processed job queues and register the name with Redis
        self._queue_id = str(uuid4())
        self._job_queue_name = JOB_QUEUE_NAME_PREFIX + self._queue_id
        self._processed_queue_name = PROCESSED_QUEUE_NAME_PREFIX + self._queue_id
        self._redis_conn.rpush(JOB_QUEUE_LIST, self._job_queue_name)
        self._logger.info("Registered job queue: {0}".format(self._job_queue_name))

        self._queued_job_ids = set()

        self._results = Queue()
        self._callback = processed_callback

        self._job_handler_exception = None
        self._job_handler_traceback = None

        self._processed_job_handler = Thread(target=self._handleProcessedJobs, daemon=True)
        self._processed_job_handler.start()

    def queueJobs(self, *args):
        """Add jobs to the queue.

        Args:
            *args: Variable length list of :class:`.Job` objects to be queued.
        """
        for job in args:
            if not isinstance(job, Job):
                err = "Cannot queue objects of '{0}'".format(type(job))
                raise ValueError(err)
            self._logger.debug("Queuing job {0}".format(job.id))
            serialized = dumps(job)
            self._queued_job_ids.add(job.id)
            self._redis_conn.rpush(self._job_queue_name, serialized)

    def _handleProcessedJobs(self):
        """Handle processed jobs returned from workers.

        This method continuously attempts to pop processed jobs off of a second job queue where
        workers return their results to and handle the results appropriately. This method is
        automatically started in another ``threading.Thread`` during the construction of a
        :class:`.QueueManager` .

        If no ``processed_callback`` is given to this :class:`.QueueManager` 's constructor, then
        handling processed jobs defaults to logging the job's reception and putting it on a
        ``Queue`` . These are retrievable via :meth:`.getResults()` .

        If ``processed_callback`` *is* given to the constructor, then handling will consist of
        calling ``processed_callback`` with the processed :class:`.Job` as its single argument.
        """
        while 1:
            try:
                ret = self._redis_conn.blpop(self._processed_queue_name)
                processed_job = loads(ret[1])

                if self._callback is None:
                    msg = "Job {0.id} returned {0.retval} with status code {0.status}"
                    self._logger.info(msg.format(processed_job))
                    self._results.put(processed_job)
                else:
                    self._callback(processed_job)
                self._queued_job_ids.remove(processed_job.id)

            except Exception as error:  # pylint: disable=broad-except
                self._job_handler_exception = error
                self._job_handler_traceback = format_exc()

    @property
    def queued_jobs_processed(self):
        """bool: Boolean indicating whether all queued jobs have been processed and handled."""
        return len(self._queued_job_ids) == 0

    @property
    def queued_job_ids(self):
        """set: Set of job IDs that have been queued, but not processed."""
        return self._queued_job_ids

    def blockUntilProcessed(self, timeout=None):
        """Block until all queued jobs have been processed and handled.

        Args:
            timeout (float, optional): How long to wait for jobs to be processed and handled.
                Defaults to ``None``, which will wait indefinitely for jobs to process and be
                handled.
        """
        if timeout is not None:
            if timeout < self._BLOCK_INTERVAL:
                interval = timeout
            else:
                interval = self._BLOCK_INTERVAL

            waited = 0.0
            while not self.queued_jobs_processed and waited < timeout:
                sleep(interval)
                waited += interval

                if self._job_handler_exception is not None:
                    self._logger.error(
                        "Error occurred in job handler thread: \n{0}".format(self._job_handler_traceback)
                    )
                    raise self._job_handler_exception

            if not self.queued_jobs_processed:
                raise JobTimeoutError(
                    "Reached timeout with {0} jobs left to process.".format(len(self._queued_job_ids))
                )

        else:
            while not self.queued_jobs_processed:
                sleep(self._BLOCK_INTERVAL)

                if self._job_handler_exception is not None:
                    self._logger.error(
                        "Error occurred in job handler thread: \n{0}".format(self._job_handler_traceback)
                    )
                    raise self._job_handler_exception

    def getResults(self):
        """Retrieve processed :class:`.Job` s for post-processing.

        Note:
            It is the user's responsibility to utilize :meth:`.blockUntilProcessed()` or
            :attr:`.queued_jobs_processed` to wait for currently queued jobs to complete. Calling
            :meth:`.getResults()`  before all jobs have been processed could result in jobs being
            left on the :attr:`._results` queue, which could lead to errors in subsequent batches
            of processing.
        """
        ret = []
        while not self._results.empty():
            ret.append(self._results.get())

        return ret

    def close(self):
        """Delete job/processed queues and un-register the names from Redis."""
        self._redis_conn.delete(self._job_queue_name)
        self._redis_conn.delete(self._processed_queue_name)
        self._redis_conn.lrem(JOB_QUEUE_LIST, 1, self._job_queue_name)

    def __del__(self):
        """Call :meth:`.close()` when :class:`.QueueManager` goes out of scope."""
        self.close()
