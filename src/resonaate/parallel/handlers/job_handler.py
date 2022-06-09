"""Defines the abstract :class:`.JobHandler` base class that specifies the common API for all parallel execution."""
# Standard Library Imports
import logging
from abc import ABCMeta, abstractmethod

# Local Imports
from ...common.exceptions import JobProcessingError, JobTimeoutError
from ...common.utilities import getTimeout
from ..job import CallbackRegistration
from ..producer import QueueManager


class JobHandler(metaclass=ABCMeta):
    """Handle creating, queuing, blocking, and post-processing jobs for parallel execution."""

    callback_class = None
    """:class:`.CallbackRegistration`: defines which callback type to register to the handler."""

    def __init__(self):
        """Initialize job handler for a parallel execution step."""
        self.logger = logging.getLogger("resonaate")
        """:class:`.Logger`: internal RESONAATE logging class."""

        self.queue_mgr = QueueManager(processed_callback=self.handleProcessedJob)
        """:class:`.QueueManager`: internal queue manager instance."""

        self.job_id_registration_dict = {}
        """``dict``: pairs of submitted :attr:`.Job.id` and corresponding :class:`.CallbackRegistration`."""

        self.callback_registry = []
        """``list``: :class:`.CallbackRegistration` objects for creating and processing :class:`.Job` objects."""

        self._total_jobs = 0
        """``int``: current total number of :class:`.Job` objects created."""

    @property
    def total_jobs(self):
        """``int``: Returns the total number of jobs submitted to the worker queue."""
        return self._total_jobs

    @abstractmethod
    def generateJobs(self, **kwargs):
        """Generate list of jobs to submit to the :class:`.QueueManager`.

        KeywordArgs:
            kwargs (``dict``): arguments specific to an implemented :class:`.JobHandler`

        Returns:
            ``list``: :class:`.Job` objects that will be submitted
        """
        raise NotImplementedError

    def registerCallback(self, registrant):
        """Register callback object that is used in parallel job creation and post-processing.

        The callback is specifically used by :meth:`~.JobHandler.executeJobs` and
        :meth:`~.Jobhandler.handleProcessedJob`.

        Args:
            registrant (``object``): reference to the registration's calling object

        Raises:
            `TypeError`: when :attr:`.callback_class` is an invalid registration type
        """
        registration = self.callback_class(registrant)  # pylint: disable=not-callable
        if not isinstance(registration, CallbackRegistration):
            raise TypeError(
                f"Use `CallbackRegistration` to register job callbacks, not {type(registration)}"
            )
        self.callback_registry.append(registration)

    @abstractmethod
    def deregisterCallback(self, callback_id):
        """Remove a registrant's :class:`.CallbackRegistration` from this :class:`.JobHandler`.

        Args:
            callback_id (any): Unique identifier of the :class:`.CallbackRegistration` being removed.
        """
        raise NotImplementedError()

    def handleProcessedJob(self, job):
        """Handle jobs completed via the :class:`.QueueManager` process.

        Hint:
            Requires implementation of :meth:`.CallbackRegistration.jobCompleteCallback`.

        Args:
            job (:class:`.Job`): parallel job object to be handled

        Raises:
            :class:`.JobProcessingError`: raised if job completed in an error state
        """
        if job.status == "processed":
            self.job_id_registration_dict[job.id].jobCompleteCallback(job)

        else:
            raise JobProcessingError(f"Error occurred in job {job.id}:\n\t{job.error}")

    def executeJobs(self, **kwargs):
        """Queue parallel job set, and wait for completion of them.

        KeywordArgs:
            kwargs (``dict``): arguments specific to an implemented :class:`.JobHandler`
        """
        jobs = self.generateJobs(**kwargs)
        self._total_jobs = len(jobs)
        self.queue_mgr.queueJobs(*jobs)

        # Wait for jobs to complete
        try:
            self.queue_mgr.blockUntilProcessed(timeout=getTimeout(self.total_jobs))
        except JobTimeoutError:
            # jobs took longer to complete than expected
            for job_id in self.queue_mgr.queued_job_ids:
                msg = (
                    f"Jobs {job_id} haven't completed after {getTimeout(self.total_jobs)} seconds"
                )
                self.logger.error(msg)

        self.job_id_registration_dict = {}
