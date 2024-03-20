""":class:`.Job` handler class that manage task prediction logic."""

from __future__ import annotations

# Standard Library Imports
from pickle import loads
from typing import TYPE_CHECKING

# Third Party Imports
from mjolnir import Job, KeyValueStore
from numpy import zeros

# Local Imports
from ..tasking.predictions import predictObservation
from .base import CallbackRegistration, JobHandler

if TYPE_CHECKING:
    # Local Imports
    from ..tasking.rewards.reward_base import Reward


def asyncCalculateReward(estimate_id: int, reward: Reward, sensor_list: list[int]) -> dict:
    """Calculate an entire row in the reward matrix for each sensor tasked to a single target.

    This calculates predicted observations and their assumed reward value.

    Hint:
        The filter that's being used needs to have :meth:`~.SequentialFilter.getForecastResult`
        implemented

    Args:
        estimate_id (``int``): ID of the :class:`.EstimateAgent` to calculate metrics for.
        reward (:class:`.Reward`): function used to calculate a sensor/estimate pair's reward.
        sensor_list (``list``): sensor `unique_id` values assigned to the current tasking engine.

    Returns:
        ``dict``: reward result dictionary contents:

        :``"visibility"``: (``ndarray``): boolean array of whether each sensor can see the estimate.
        :``"reward_matrix"``: (``ndarray``): numeric reward array for each sensor.
        :``"estimate_id"``: (``int``): ID of the :class:`.EstimateAgent` to calculate metrics for.
    """
    sensor_agents = loads(KeyValueStore.getValue("sensor_agents"))
    estimate_agents = loads(KeyValueStore.getValue("estimate_agents"))
    estimate = estimate_agents[estimate_id]

    # Ensure the visibility and metric matrices are the same scale as in the tasking engine
    visibility = zeros(len(sensor_list), dtype=bool)
    metric_matrix = zeros((len(sensor_list), len(reward.metrics)), dtype=float)

    for sensor_index, sensor_id in enumerate(sensor_list):
        sensor_agent = sensor_agents[sensor_id]

        # Attempt predicted observations, in order to perform sensor tasking
        # Only calculate metrics if the estimate is observable
        if predicted_observation := predictObservation(sensor_agent, estimate):
            # This is required to update the metrics attached to the UKF/KF for this observation
            estimate.nominal_filter.forecast([predicted_observation])
            visibility[sensor_index] = True
            metric_matrix[sensor_index] = reward.calculateMetrics(estimate, sensor_agent)

    return {
        "estimate_id": estimate_id,
        "visibility": visibility,
        "metric_matrix": metric_matrix,
    }


class TaskPredictionRegistration(CallbackRegistration):
    """Callback registration for :class:`.Task` prediction jobs."""

    def jobCreateCallback(self, **kwargs):
        """Create a :func:`.asyncCalculateReward` job.

        This relies on a common interface for :meth:`.SequentialFilter.forecast` and for
        :meth:`.Sensor.attemptObservation`.

        KeywordArgs:
            estimate_id (``int``): ID associated with the :class:`.EstimateAgent`.

        Returns:
            :class:`.Job`: Job to be processed in parallel.
        """
        return Job(
            asyncCalculateReward,
            args=[kwargs["estimate_id"], self.registrant.reward, self.registrant.sensor_list],
        )

    def jobCompleteCallback(self, job):
        """Save the reward and visibility values for this job.

        These values pertain to an entire row of the respective matrices.

        Args:
            job (:class:`.Job`): job object that's returned when a job completes.
        """
        row = self.registrant.target_list.index(job.retval["estimate_id"])
        self.registrant.visibility_matrix[row] = job.retval["visibility"]
        self.registrant.metric_matrix[row] = job.retval["metric_matrix"]


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
