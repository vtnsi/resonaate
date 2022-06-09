""":class:`.Job` handler class that manages estimate prediction logic."""
# Standard Library Imports
# Pip Package Imports
# RESONAATE Imports
from .agent_propagation import PropagationJobHandler
from ..async_functions import asyncPredict
from ..job import CallbackRegistration, Job


class EstimatePredictionRegistration(CallbackRegistration):
    """Callback registration for :class:`.Estimate` prediction jobs."""

    def jobCreateCallback(self, **kwargs):
        """Create a :func:`.asyncPredict` job & update :attr:`~.Agent.time` appropriately.

        This relies on a common interface for :meth:`.SequentialFilter.predict`.

        KeywordArgs:
            new_time (:class:`.ScenarioTime`): payload indicating the current simulation time.

        Returns
            :class:`.Job`: job to be processed by :class:`.QueueManager`.
        """
        new_time = kwargs["new_time"]
        job = Job(
            asyncPredict,
            args=[
                self.registrant.nominal_filter,
                new_time
            ]
        )
        self.registrant.time = new_time

        return job

    def jobCompleteCallback(self, job):
        """Save the *a priori* :attr:`.state_estimate` and :attr:`.error_covariance`.

        Also, update the :class:`.SequentialFilter` associated with the agent.

        Args:
            job (:class:`.Job`): job object that's returned when a job completes.
        """
        self.registrant.updateFromAsyncPredict(job.retval)


class EstimatePredictionJobHandler(PropagationJobHandler):
    """Handle the parallel jobs during the :class:`.Estimate` prediction step of the simulation."""

    callback_class = EstimatePredictionRegistration
