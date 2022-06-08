"""Control module for managing worker processes."""

from multiprocessing import Process, Lock, cpu_count
from threading import Thread
from time import time, sleep
from pickle import loads, dumps
from os import kill, getpid
from signal import SIGINT
from datetime import datetime

from . import TASK_QUEUE_LIST, PROCESSED_QUEUE_NAME_PREFIX, MASTER_KEY_NAME
from . import getRedisConnection, REDIS_QUEUE_LOGGER, masterExists, getMasterHash
from ..common.behavioral_config import BehavioralConfig


class WorkerManager:
    """Class for managing worker processes."""

    WATCHDOG_INTERVAL = 3
    """int: Interval on which the watchdog thread operates."""

    WATCHDOG_TERMINATE_AFTER = 15
    """int: Number of seconds a worker can spend processing a single task before being terminated."""

    def __init__(self, proc_count=None, daemonic=False, logger=None):
        """Instantiate a :class:`.WorkerManager` object.

        Args:
            proc_count (int): Number of worker processes to spin up.
            daemonic (bool): Flag indicating whether worker threads should be daemonic or not. If
                worker threads are not flagged as daemonic, then it is up to the user to call
                :meth:`.stopWorkers()` or de-scope this :class:`.WorkerManager` instance to clean
                up the workers before the program ends.
            logger (logging.Logger, optional): Custom logging instance for :class:`.WorkerManager`
                and its workers to use, instead of :attr:`.REDIS_QUEUE_LOGGER` .
        """
        if logger is not None:
            self._logger = logger
        else:
            self._logger = REDIS_QUEUE_LOGGER

        if not proc_count:
            proc_count = BehavioralConfig.getConfig().parallel.WorkerCount

        self._worker_processes = []
        self._worker_locks = []

        # make sure redis is up before trying to start worker threads, that way if connection is
        #   bad, only one exception is thrown rather than `proc_count`
        self._redis_conn = getRedisConnection()
        self._redis_conn.get(MASTER_KEY_NAME)

        self._processing_queue_name = "processing-{0}".format(getMasterHash())

        if proc_count is None:
            proc_count = cpu_count()

        for item in range(proc_count):
            self._worker_locks.append(Lock())
            worker_name = 'worker-{0}-{1}'.format(item, getMasterHash()[:8])

            self._worker_processes.append(
                Process(
                    target=workerLoop,
                    args=(worker_name, self._worker_locks[item], self._processing_queue_name),
                    kwargs={"logger": logger},
                    name=worker_name,
                    daemon=daemonic
                )
            )

        self._watchdog_thread = Thread(target=self._watchdogLoop, daemon=True)

    def startWorkers(self, watchdog=True):
        """Start worker processes.

        Args:
            watchdog (bool,optional): Flag indicating whether the watchdog thread should be
                started. This is useful in the case where there will be multiple instances of
                :class:`.WorkerManager` 's since only one of them needs to track the the processing
                Redis queue since all instances will report to the same Redis server.
        """
        for proc in self._worker_processes:
            proc.start()

        if watchdog:
            self._watchdog_thread.start()

    def stopWorkers(self, no_wait=False):
        """Stop worker processes.

        Args:
            no_wait (bool, optional): Flag indicating whether to wait for worker processes to
                finish their current processing before terminating them.
        """
        if no_wait:
            for proc in self._worker_processes:
                proc.terminate()

        else:
            for lock, proc in zip(self._worker_locks, self._worker_processes):
                with lock:
                    proc.terminate()

    @property
    def is_processing(self):
        """bool: Boolean indicating whether one or more workers are still processing."""
        for lock in self._worker_locks:
            if not lock.acquire(block=False):
                return True
            else:
                lock.release()

        return False

    def _watchdogLoop(self):  # noqa: C901
        """Terminate workers that take too long to finish processing."""
        workers_processing = {}

        def currentWorkerProcessingDuration(worker):
            """Return how long a worker has been processing a single task.

            Args:
                worker (str): Name of worker to determine processing duration.

            Return:
                float: Number of seconds the worker has been processing.
            """
            tasking = workers_processing.get(worker, (None, None))

            if tasking[0] is not None:
                return time() - tasking[1]

            else:
                return 0.0

        total_proc_time = 0.0
        total_tasks_processed = 0
        last_average_log = 0.0
        while 1:
            serialized = self._redis_conn.blpop(self._processing_queue_name, timeout=self.WATCHDOG_INTERVAL)
            if serialized is not None:
                new_tasking = loads(serialized[1])

                if new_tasking[1] is None:
                    # task has finished
                    try:
                        prev_tasking = workers_processing[new_tasking[0]]
                    except KeyError:
                        pass
                    else:
                        total_proc_time += new_tasking[2] - prev_tasking[1]
                        total_tasks_processed += 1

                workers_processing[new_tasking[0]] = new_tasking[1:]

            if time() - last_average_log > self.WATCHDOG_TERMINATE_AFTER:
                if total_tasks_processed > 0:
                    self._logger.info("Average task processing time: {0}".format(
                        total_proc_time / total_tasks_processed
                    ))

                    for worker_id, tasking in workers_processing.items():
                        self._logger.info("'{0}' working on task '{1}' since {2}".format(
                            worker_id,
                            tasking[0],
                            datetime.utcfromtimestamp(tasking[1]).isoformat()
                        ))

                    last_average_log = time()

            for worker in self._worker_processes:
                if currentWorkerProcessingDuration(worker.name) > self.WATCHDOG_TERMINATE_AFTER:
                    msg = "Terminating worker '{0}' because it's been processing task '{1}' for more than {2} seconds."
                    self._logger.warning(
                        msg.format(
                            worker.name,
                            workers_processing[worker.name][0],
                            self.WATCHDOG_TERMINATE_AFTER
                        )
                    )
                    kill(worker.pid, SIGINT)

                    del workers_processing[worker.name]

    def __del__(self):
        """Close workers when this :class:`.WorkerManager` instance goes out of scope."""
        self.stopWorkers(no_wait=True)
        self._redis_conn.delete(self._processing_queue_name)


def workerLoop(name, lock, processing_queue_name, logger=None):
    """Start a worker thread loop.

    Continuously pop :class:`.Task` s off of the task queue and process them.

    Args:
        name (str): Name for the process that started this worker loop.
        lock (multiprocessing.Lock): Lock used to indicate when processing is taking place vs when
            the worker loop is blocked on trying to pop its next task off the queue.
        processing_queue_name (str): Name of Redis queue to use to report worker's tasking.
        logger (logging.Logger, optional): Custom logging instance for :meth:`.workerLoop` to use,
            instead of :attr:`.REDIS_QUEUE_LOGGER` .
    """
    if logger is None:
        logger = REDIS_QUEUE_LOGGER

    name = "{0}-{1}".format(name, getpid())
    try:
        redis_conn = getRedisConnection()

        while masterExists(redis_connection=redis_conn):
            logger.debug("{0} - Waiting for task...".format(name))

            # Get a list of registered task queue names
            task_queue_names = redis_conn.lrange(TASK_QUEUE_LIST, 0, -1)
            if len(task_queue_names) > 0:
                # Decode the list of task queue names so they are Python strings
                task_queue_names = [name.decode() for name in task_queue_names]
            else:
                # If no task queues are registered yet, wait until there are
                sleep(1)
                continue

            serialized = redis_conn.blpop(task_queue_names, timeout=1)

            if serialized:
                with lock:
                    task_queue_name = serialized[0].decode()
                    task_queue_id = task_queue_name.split('_')[-1]
                    task = loads(serialized[1])

                    redis_conn.rpush(processing_queue_name, dumps((name, task.id, time())))

                    logger.debug("{0} - Working on task {1} from {2}...".format(name, task.id, task_queue_id))
                    task.process()

                    processed_queue_name = PROCESSED_QUEUE_NAME_PREFIX + task_queue_id
                    logger.debug("{0} - Returning task {1} to {2}.".format(name, task.id, processed_queue_name))

                    redis_conn.rpush(processed_queue_name, dumps(task))
                    redis_conn.rpush(processing_queue_name, dumps((name, None, time())))
        logger.info("{0} - Master seems to no longer exist. Exiting.".format(name))

    except KeyboardInterrupt:
        logger.warning("{0} - Received KeyboardInterrupt. Terminating...".format(name))
