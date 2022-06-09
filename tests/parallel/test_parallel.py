# pylint: disable=attribute-defined-outside-init, unused-argument
# Standard Library Imports
import time

# Third Party Imports
import numpy as np
import pytest

try:
    # RESONAATE Imports
    from resonaate.common.exceptions import JobTimeoutError
    from resonaate.parallel import REDIS_QUEUE_LOGGER
    from resonaate.parallel.job import Job
    from resonaate.parallel.producer import QueueManager
    from resonaate.parallel.worker import WorkerManager
except ImportError as error:
    raise Exception(f"Please ensure you have appropriate packages installed:\n {error}") from error
# Local Imports
# Testing Imports
from ..conftest import BaseTestCase


def testJobClass():
    """Test basic functionality of Job classes."""
    func = np.abs
    val = -10.5433
    job = Job(func, [val])
    assert job.status == "unprocessed"
    assert job.error is None
    job.process()
    assert job.status == "processed"
    assert job.error is None
    assert job.retval == func(val)

    # Bad value, returns error
    job = Job(func, [None])
    job.process()
    assert job.status == "failed"
    assert job.error is not None

    # Bad function, error raised
    with pytest.raises(TypeError):
        job = Job(None, val)


@pytest.mark.usefixtures("redis_setup")
class TestWorkerManager(BaseTestCase):
    """Test proper usage of WorkerManager class."""

    def testCreation(self):
        """Test basic functionality of WorkerManager class."""
        worker_manager = WorkerManager(proc_count=1, daemonic=True, logger=REDIS_QUEUE_LOGGER)
        worker_manager.startWorkers()
        assert worker_manager.is_processing is False
        worker_manager.stopWorkers(no_wait=False)
        del worker_manager

    def testGoodJob(self, worker_manager, queue_manager, numpy_add_job):
        """Test doing a good job with WorkerManager."""
        queue_manager.queueJobs(numpy_add_job)

    def testDeletion(self):
        """Test deleting a WorkerManager."""
        worker_manager = WorkerManager(proc_count=1, daemonic=True, logger=REDIS_QUEUE_LOGGER)
        worker_manager.startWorkers()
        del worker_manager

    def testLongJob(self, worker_manager, queue_manager, sleep_job_1s):
        """Test a job that takes some nontrivial amount of time."""
        queue_manager.queueJobs(sleep_job_1s)
        queue_manager.blockUntilProcessed()
        assert worker_manager.is_processing is False

    @pytest.mark.skip(reason="This fails randomly...IDK how to guarantee it succeeds.")
    def testTooLongJob(self, monkeypatch, worker_manager, queue_manager, sleep_job_6s):
        """Test doing a job longer than interval and timeout with WorkerManager."""
        with monkeypatch.context() as m_patch:
            m_patch.setattr(worker_manager, "WATCHDOG_INTERVAL", 1)
            m_patch.setattr(worker_manager, "WATCHDOG_TERMINATE_AFTER", 1)

            # Start workers and queue sleep job
            queue_manager.queueJobs(sleep_job_6s)
            time.sleep(0.1)
            assert worker_manager.is_processing is True
            queue_manager.blockUntilProcessed()

            # Check for log, doesn't seem to work?
            # for record_tuple in caplog.record_tuples:
            #     if "Terminating worker" in record_tuple:
            #         break
            # else:
            #     assert False


@pytest.mark.usefixtures("redis_setup", "worker_manager")
class TestQueueManager(BaseTestCase):
    """Test proper usage of QueueManager class."""

    def jobCallback(self, job):
        """Dummy callback function to check the job completed."""
        assert job.retval is not None

    def testCreation(self):
        """Test basic functionality of QueueManager class."""
        queue_manager = QueueManager(logger=REDIS_QUEUE_LOGGER)
        assert queue_manager.queued_jobs_processed is True
        queue_manager.close()

    def testGoodJob(self, queue_manager, numpy_add_job, sleep_job_1s):
        """Test using a good job with QueueManager."""
        queue_manager.queueJobs(numpy_add_job, sleep_job_1s)

    def testBadJob(self, queue_manager):
        """Test using a bad job with QueueManager."""
        job = {"function": np.add}  # improper job type
        with pytest.raises(TypeError):
            queue_manager.queueJobs(job)

    def testDeletion(self, queue_manager):
        """Test deleting a QueueManager."""
        del queue_manager

    def testCompletedJobNoCallback(self, queue_manager, numpy_add_job):
        """Test completing job with no callback, use getResults()."""
        queue_manager.queueJobs(numpy_add_job)
        assert len(queue_manager.queued_job_ids) > 0
        queue_manager.blockUntilProcessed()
        assert queue_manager.getResults()[0].retval == 1 + 2
        assert queue_manager.queued_jobs_processed

    def testCompletedJobCallback(self, numpy_add_job):
        """Test completing job with a callback function."""
        queue_manager = QueueManager(
            processed_callback=self.jobCallback, logger=REDIS_QUEUE_LOGGER
        )
        queue_manager.queueJobs(numpy_add_job)
        assert len(queue_manager.queued_job_ids) > 0
        queue_manager.blockUntilProcessed()
        assert queue_manager.queued_jobs_processed

    def testBadJobCallback(self, numpy_add_job):
        """Test completing job with a poorly formed callback function."""
        queue_manager = QueueManager(processed_callback=np.dot, logger=REDIS_QUEUE_LOGGER)
        queue_manager.queueJobs(numpy_add_job)
        assert len(queue_manager.queued_job_ids) > 0

        # timeout
        with pytest.raises(TypeError):
            queue_manager.blockUntilProcessed()

        # no timeout
        with pytest.raises(TypeError):
            queue_manager.blockUntilProcessed(timeout=0.1)

    def testTimeout(self, queue_manager, sleep_job_1s):
        """Test calling blockUntilProcessed with a timeout."""
        queue_manager.queueJobs(sleep_job_1s)
        assert len(queue_manager.queued_job_ids) > 0
        queue_manager.blockUntilProcessed(timeout=5)
        assert queue_manager.queued_jobs_processed

    def testTimeoutError(self, queue_manager, sleep_job_3s):
        """Test calling blockUntilProcessed with a short timeout."""
        queue_manager.queueJobs(sleep_job_3s)
        assert len(queue_manager.queued_job_ids) > 0
        with pytest.raises(JobTimeoutError):
            queue_manager.blockUntilProcessed(timeout=1)
