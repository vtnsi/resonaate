# pylint: disable=attribute-defined-outside-init, no-self-use, unused-argument
# Standard Library Imports
import time
# Third Party Imports
import numpy as np
import pytest
# RESONAATE Imports
try:
    from resonaate.parallel import setUpLogger, REDIS_QUEUE_LOGGER
    from resonaate.parallel.job import Job
    from resonaate.parallel.producer import QueueManager
    from resonaate.parallel.worker import WorkerManager
except ImportError as error:
    raise Exception(
        f"Please ensure you have appropriate packages installed:\n {error}"
    ) from error
# Testing Imports


@pytest.fixture(scope="function", name="redis_setup")
def setupRedis(redis):
    """Setup redis instance and logger."""
    setUpLogger()


@pytest.fixture(scope="function", name="worker_manager")
def createWorkerManager():
    """Create a valid WorkerManager."""
    worker_manager = WorkerManager(proc_count=1, daemonic=True, logger=REDIS_QUEUE_LOGGER)
    worker_manager.startWorkers()
    yield worker_manager
    worker_manager.stopWorkers(no_wait=True)
    worker_manager.__del__()


@pytest.fixture(scope="function", name="queue_manager")
def createQueueManager():
    """Create a valid QueueManager."""
    queue_manager = QueueManager(processed_callback=None, logger=REDIS_QUEUE_LOGGER)
    yield queue_manager
    queue_manager.__del__()


@pytest.fixture(scope="function", name="numpy_add_job")
def getAddJob():
    """Create Job to call np.add with [1, 2] as arguments."""
    yield Job(np.add, args=[1, 2])


@pytest.fixture(scope="function", name="sleep_job_1s")
def getShortSleepJob():
    """Create Job to call time.sleep for 3 seconds."""
    yield Job(time.sleep, args=[1])


@pytest.fixture(scope="function", name="sleep_job_3s")
def getMedSleepJob():
    """Create Job to call time.sleep for 3 seconds."""
    yield Job(time.sleep, args=[3])


@pytest.fixture(scope="function", name="sleep_job_6s")
def getLongSleepJob():
    """Create Job to call time.sleep for very long time, be careful!."""
    yield Job(time.sleep, args=[6])
