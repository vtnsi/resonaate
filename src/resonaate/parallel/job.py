"""Defines the :class:`.Job` and :class:`.CallbackRegistration` classes."""
# Standard Library Imports
from abc import ABCMeta, abstractmethod
from functools import partial
from traceback import format_exc


class Job:
    """Class that encapsulates a job to be completed by a :class:`.Worker`.

    Attributes:
        id (``str``): Unique identifier for this job.
        function (``functools.partial``): Function that gets called when :class:`.Job` is processed. Note that
            this function must have a non-``None`` return value because of the parallel processing
            context.
        retval (any): Return value of :attr:`.function`. Initialized as ``None``, and populated
            once this :class:`.Job` has been processed.
        error (``str``): Exception traceback thrown by :attr:`.function`. Initialized as ``None``, and
            populated if an exception is thrown during processing.
    """

    _JOB_ID_ITER = 0

    def __init__(self, method, args=None, kwargs=None):
        """Instantiate a :class:`.Job` object.

        Args:
            method (``callable``): Function that this :class:`.Job` will be executing.
            args (``list``, optional): Variable length argument list for ``method``.
            kwargs (``dict``, optional): Keyword arguments for ``method``.
        """
        if args is None:
            args = []
        if kwargs is None:
            kwargs = {}
        self.function = partial(method, *args, **kwargs)
        self.id = str(Job._JOB_ID_ITER)  # pylint: disable=invalid-name
        Job._JOB_ID_ITER += 1
        self.retval = None
        self.error = None

    def process(self):
        """Execute the :attr:`.function`."""
        try:
            self.retval = self.function()
        except Exception:  # pylint: disable=broad-except
            self.error = format_exc()

    @property
    def status(self):
        """``str``: String indicating :class:`.Job`'s status: 'unprocessed', 'processed', or 'failed'."""
        if self.retval is None and self.error is None:
            status = "unprocessed"
        elif self.error is None and self.retval is not None:
            status = "processed"
        elif self.retval is None and self.error is not None:
            status = "failed"
        return status


class CallbackRegistration(metaclass=ABCMeta):
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

        Returns
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
