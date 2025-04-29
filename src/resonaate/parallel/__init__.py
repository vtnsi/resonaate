"""Module defining common infrastructure code for distributing processes via Ray."""

# Standard Library Imports
from abc import ABC, abstractmethod

# Third Party Imports
import ray


class Registration(ABC):
    """Encapsulates data needed to produce and process a unit of work."""

    def __init__(self, registrant):
        """Initialize a :class:`.Registration`.

        Args:
            registrant: The entity requesting that a unit of work be processed.
        """
        self._registrant = registrant

    @abstractmethod
    def generateSubmission(self):
        """Return the relevant submission object representing the current unit of work."""
        raise NotImplementedError

    @abstractmethod
    def processResults(self, results):
        """Process the results of a processed submission."""
        raise NotImplementedError


class JobExecutor(ABC):
    """Creates, executes, and processes the results of jobs in batches."""

    def __init__(self):
        """Initialize a :class:`.JobExecutor`."""
        self._unfinished_jobs: list = []
        self._result_reg_mapping: dict = {}

    @classmethod
    @abstractmethod
    def getRemoteFunc(cls):
        """Pointer to function being executed on remote worker."""
        raise NotImplementedError

    def enqueueJob(self, registration: Registration):
        """Delegate a specified registration of work to be processed remotely.

        Args:
            registration: Registration encapsulating the unit of work to be executed.
        """
        submission = registration.generateSubmission()
        remote_ref = self.getRemoteFunc().remote(submission)
        self._unfinished_jobs.append(remote_ref)
        self._result_reg_mapping[remote_ref] = registration

    def join(self):
        """Wait for all enqueued jobs to complete and be processed."""
        while self._unfinished_jobs:
            finished_jobs, self._unfinished_jobs = ray.wait(self._unfinished_jobs)
            result = ray.get(finished_jobs[0])
            self._result_reg_mapping[finished_jobs[0]].processResults(result)
            del self._result_reg_mapping[finished_jobs[0]]
