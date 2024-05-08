"""Defines abstract base classes used throughout the ``job_handlers`` subpackage."""

from __future__ import annotations

# Standard Library Imports
import logging
from abc import ABC, abstractmethod

# Third Party Imports
from strmbrkr import Job, JobTimeoutError, QueueManager

# Local Imports
from ..common.exceptions import JobProcessingError
from ..common.utilities import getTimeout


class ParallelMixin(ABC):
    """Class which provides an interface for all parallel-related classes.

    This class is intended to be subclassed by a class which contains parallel processing
    code. The purpose it to enforce good practices for parallel processing by requiring
    certain methods be explicitly defined.
    """

    @abstractmethod
    def shutdown(self):
        """Properly shutdown the parallel processing jobs & managers.

        This method should be called once the class is no longer used. This method must be
        overridden by all subclasses. The defined method should call any necessary shutdown
        logic internal to the class, including calling :meth:`.shutdown` on any contained classes.
        """
        raise NotImplementedError


class CallbackRegistration(ABC):
    """Abstract registration that is registered to a :attr:`~.JobHandler.callback_registry`."""

    def __init__(self, registrant):
        """Initialize a callback registration defining parallel job handling.

        Args:
            registrant (``object``): reference to the registration's calling object.
        """
        self.registrant = registrant

    @abstractmethod
    def jobCreateCallback(self, **kwargs):
        """Create a job to be processed in parallel.

        KeywordArgs:
            kwargs (``dict``): arguments specific to an implemented :class:`.CallbackRegistration`.

        Returns:
            :class:`.Job`: job to be processed by :class:`.QueueManager`.
        """
        raise NotImplementedError

    @abstractmethod
    def jobCompleteCallback(self, job):
        """Process a completed :class:`.Job`'s results.

        Args:
            job (:class:`.Job`): job that's returned when a job completes.
        """
        raise NotImplementedError


class JobHandler(ParallelMixin, ABC):
    """Handle creating, queuing, blocking, and post-processing jobs for parallel execution."""

    callback_class = None
    """:class:`.CallbackRegistration`: defines which callback type to register to the handler."""

    def __init__(self, dump_on_timeout: bool = True):
        """Initialize job handler for a parallel execution step.

        Args:
            dump_on_timeout (``bool``, optional): whether the KVS dumps state on timeout errors.
                Mostly for testing. Defaults to ``True``.
        """
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

        self._dump_on_timeout = dump_on_timeout
        """``bool``: controls whether KVS will dump its state on a timeout error."""

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
        :meth:`~.JobHandler.handleProcessedJob`.

        Args:
            registrant (``object``): reference to the registration's calling object

        Raises:
            `TypeError`: when :attr:`.callback_class` is an invalid registration type
        """
        registration = self.callback_class(registrant)
        if not isinstance(registration, CallbackRegistration):
            raise TypeError(
                f"Use `CallbackRegistration` to register job callbacks, not {type(registration)}",
            )
        self.callback_registry.append(registration)

    @abstractmethod
    def deregisterCallback(self, callback_id):
        """Remove a registrant's :class:`.CallbackRegistration` from this :class:`.JobHandler`.

        Args:
            callback_id (any): Unique identifier of the :class:`.CallbackRegistration` being removed.
        """
        raise NotImplementedError

    def handleProcessedJob(self, job):
        """Handle jobs completed via the :class:`.QueueManager` process.

        Hint:
            Requires implementation of :meth:`.CallbackRegistration.jobCompleteCallback`.

        Args:
            job (:class:`.Job`): parallel job object to be handled

        Raises:
            :class:`.JobProcessingError`: raised if job completed in an error state
        """
        if job.status == Job.Status.PROCESSED:
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
            self.queue_mgr.blockUntilProcessed(
                timeout=getTimeout(self.total_jobs),
                dump_on_timeout=self._dump_on_timeout,
            )
        except JobTimeoutError:
            # jobs took longer to complete than expected
            for job_id in self.queue_mgr.queued_job_ids:
                msg = (
                    f"Jobs {job_id} haven't completed after {getTimeout(self.total_jobs)} seconds"
                )
                self.logger.error(msg)

        self.job_id_registration_dict = {}

    def shutdown(self):
        """Shutdown the :class:`.QueueManager`."""
        self.queue_mgr.stopHandling()
