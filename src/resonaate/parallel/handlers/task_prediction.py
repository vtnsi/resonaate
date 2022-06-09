""":class:`.Job` handler class that manage task prediction logic."""
# Standard Library Imports
# Third Party Imports
# RESONAATE Imports
from .job_handler import JobHandler
from ..async_functions import asyncCalculateReward
from ..job import CallbackRegistration, Job


class TaskPredictionRegistration(CallbackRegistration):
    """Callback registration for :class:`.Task` prediction jobs."""

    def jobCreateCallback(self, **kwargs):
        """Create a :func:`.asyncCalculateReward` job.

        This relies on a common interface for :meth:`.SequentialFilter.forecast` and for
        :meth:`.Sensor.makeObservation`.

        KeywordArgs:
            estimate_id (``int``): ID associated with the :class:`.EstimateAgent`.

        Returns
            :class:`.Job`: Job to be processed in parallel.
        """
        return Job(
            asyncCalculateReward,
            args=[
                kwargs["estimate_id"],
                self.registrant.reward,
                self.registrant.sensor_list
            ]
        )

    def jobCompleteCallback(self, job):
        """Save the reward and visibility values for this job.

        These values pertain to an entire row of the respective matrices.

        Args:
            job (:class:`.Job`): job object that's returned when a job completes.
        """
        row = self.registrant.target_list.index(job.retval["estimate_id"])
        self.registrant.visibility_matrix[row] = job.retval["visibility"]
        self.registrant.reward_matrix[row] = job.retval["reward_matrix"]


class TaskPredictionJobHandler(JobHandler):
    """Handle the parallel jobs during the :class:`.Task` prediction step of the simulation."""

    callback_class = TaskPredictionRegistration

    def generateJobs(self, **kwargs):
        """Generate list of observation prediction jobs to submit to the :class:`.QueueManager`.

        Returns:
            ``list``: :class:`.Job` objects that will be submitted
        """
        jobs = []
        for registration in self.callback_registry:
            for estimate_id in registration.registrant.target_list:
                job = registration.jobCreateCallback(estimate_id=estimate_id)
                self.job_id_registration_dict[job.id] = registration
                jobs.append(job)

        return jobs

    def deregisterCallback(self, callback_id):
        """Remove a registrant's :class:`.CallbackRegistration` from this :class:`.JobHandler`.

        Note:
            The only expected registrant for a :class:`.TaskPredictionJobHandler` is the :class:`.TaskingEngine` that
            instantiated this handler. Because of this, there's no need to actually "deregister" anything. Instead, it
            should be sufficient to just remove an :attr:`.Agent.simulation_id` from the relevant
            :attr:`.TaskingEngine.target_list` or :attr:`.TaskingEngine.sensor_list`.

        Args:
            callback_id (any): Unique identifier of the :class:`.CallbackRegistration` being removed.
        """
