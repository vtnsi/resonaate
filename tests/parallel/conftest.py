# pylint: disable=unused-argument
from __future__ import annotations

# Standard Library Imports
import time
from typing import TYPE_CHECKING

# Third Party Imports
import numpy as np
import pytest

# RESONAATE Imports
from resonaate.parallel import REDIS_QUEUE_LOGGER, setUpLogger
from resonaate.parallel.job import Job
from resonaate.parallel.producer import QueueManager
from resonaate.parallel.worker import WorkerManager

# Type Checking Imports
if TYPE_CHECKING:
    # RESONAATE Imports
    from resonaate.parallel import Redis


@pytest.fixture(name="redis_setup")
def _setupRedis(redis: Redis) -> None:
    """Setup redis instance and logger."""
    setUpLogger()


@pytest.fixture(name="worker_manager")
def createWorkerManager() -> WorkerManager:
    """Create a valid WorkerManager."""
    worker_manager = WorkerManager(proc_count=1, daemonic=True, logger=REDIS_QUEUE_LOGGER)
    worker_manager.startWorkers()
    yield worker_manager
    worker_manager.stopWorkers(no_wait=True)
    worker_manager.shutdown()


@pytest.fixture(name="queue_manager")
def createQueueManager() -> QueueManager:
    """Create a valid QueueManager."""
    queue_manager = QueueManager(processed_callback=None, logger=REDIS_QUEUE_LOGGER)
    yield queue_manager
    queue_manager.shutdown()


@pytest.fixture(name="numpy_add_job")
def getAddJob() -> Job:
    """Create Job to call np.add with [1, 2] as arguments."""
    return Job(np.add, args=[1, 2])


@pytest.fixture(name="sleep_job_1s")
def getShortSleepJob() -> Job:
    """Create Job to call time.sleep for 3 seconds."""
    return Job(time.sleep, args=[1])


@pytest.fixture(name="sleep_job_3s")
def getMedSleepJob() -> Job:
    """Create Job to call time.sleep for 3 seconds."""
    return Job(time.sleep, args=[3])


@pytest.fixture(name="sleep_job_6s")
def getLongSleepJob() -> Job:
    """Create Job to call time.sleep for very long time, be careful!."""
    return Job(time.sleep, args=[6])
