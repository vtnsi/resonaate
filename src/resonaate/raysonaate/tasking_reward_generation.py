from __future__ import annotations

# Standard Library Imports
from dataclasses import dataclass
from typing import TYPE_CHECKING

# Third Party Imports
import ray
from numpy import zeros

# Local Imports
from ..tasking.predictions import predictObservation
from . import JobExecutor, Registration

if TYPE_CHECKING:
    # Third Party Imports
    from numpy import ndarray

    # Local Imports
    from ..agents.estimate_agent import EstimateAgent
    from ..agents.sensing_agent import SensingAgent
    from ..tasking.engine.engine_base import TaskingEngine
    from ..tasking.rewards import Reward


@dataclass
class RewardCalcSubmission:

    estimate_handle: EstimateAgent
    """Remote handle of the :class;`.EstimateAgent` to calculate reward for."""

    reward: Reward
    """Function used to calculate a sensor/estimate pair's reward."""

    sensor_handle_list: list[SensingAgent]
    """List of remote handles of the :class:`.SensingAgent`s task-able by the calling engine."""


@dataclass
class RewardCalcResult:

    estimate_id: int
    """Unique identifier of the :class:`.EstimateAgent` that rewards were calculated for."""

    visibility: ndarray
    """Boolean array of whether each sensor can see the estimate."""

    metric_matrix: ndarray
    """Numeric reward array for each sensor."""


@ray.remote
def asyncCalculateReward(submission: RewardCalcSubmission) -> RewardCalcResult:
    """Calculate an entire row in the reward matrix for each sensor tasked to a single target.

    This calculates predicted observations and their assumed reward value.

    Hint:
        The filter that's being used needs to have :meth:`~.SequentialFilter.getForecastResult`
        implemented

    Args:
        submission: Encapsulation of attributes specifying reward calculation.

    Returns:
        Result of reward calculation.
    """
    estimate: EstimateAgent = ray.get(submission.estimate_handle)

    # Ensure the visibility and metric matrices are the same scale as in the tasking engine
    visibility = zeros(len(submission.sensor_handle_list), dtype=bool)
    metric_matrix = zeros((len(submission.sensor_handle_list), len(submission.reward.metrics)), dtype=float)

    sensor_list = ray.get(submission.sensor_handle_list)
    for sensor_index, sensor_agent in enumerate(sensor_list):
        # Attempt predicted observations, in order to perform sensor tasking
        # Only calculate metrics if the estimate is observable
        if predicted_observation := predictObservation(sensor_agent, estimate):
            # This is required to update the metrics attached to the UKF/KF for this observation
            estimate.nominal_filter.forecast([predicted_observation])
            visibility[sensor_index] = True
            metric_matrix[sensor_index] = submission.reward.calculateMetrics(estimate, sensor_agent)

    return RewardCalcResult(
        estimate_id=estimate.simulation_id,
        visibility=visibility,
        metric_matrix=metric_matrix
    )


class TaskingRewardRegistration(Registration):

    def __init__(self, registrant: TaskingEngine, estimate_id: int):
        """Initialize a :class:`.TaskingRewardRegistration`.

        Args:
            registrant: The :class:`.TaskingEngine` requesting this segment of the reward be
                calculated.
            estimate_id: The unique identifier of the :class:`.EstimateAgent` the tasking reward
                will be calculated for.
        """
        super().__init__(registrant)
        self._estimate_id = estimate_id
    
    def generateSubmission(self) -> RewardCalcSubmission:
        """Generate a :class:`.RewardCalcSubmission` specifying the reward being calculated."""
        raise Exception("Don't actually call this.")

    def processResults(self, results: RewardCalcResult):
        """Update the :attr:`._registrant`'s visibility and metric matrices."""
        row = self._registrant.target_list.index(results.estimate_id)
        self._registrant.visibility_matrix[row] = results.visibility
        self._registrant.metric_matrix[row] = results.metric_matrix


class TaskingRewardExecutor(JobExecutor):

    def __init__(self, tasking_engine: TaskingEngine):
        super().__init__()
        self._tasking_engine = tasking_engine

    @classmethod
    def getRemoteFunc(cls):
        return asyncCalculateReward

    def execute(self):
        sensor_handle_list = [self._tasking_engine._sensor_store[sensor_id] for sensor_id in self._tasking_engine.sensor_list]
        for registration in self._registrations:
            submission = RewardCalcSubmission(
                self._tasking_engine._estimate_store[registration._estimate_id],
                reward=self._tasking_engine.reward,
                sensor_handle_list=sensor_handle_list,
            )

            remote_ref = self.getRemoteFunc().remote(submission)
            self._unfinished_jobs.append(remote_ref)
            self._result_reg_mapping[remote_ref] = registration

        while self._unfinished_jobs:
            finished_jobs, self._unfinished_jobs = ray.wait(self._unfinished_jobs)
            result = ray.get(finished_jobs[0])
            self._result_reg_mapping[finished_jobs[0]].processResults(result)
