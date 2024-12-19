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
from .agent_store import getEstimateStore, getSensorStore

if TYPE_CHECKING:
    # Third Party Imports
    from numpy import ndarray

    # Local Imports
    from ..tasking.engine.engine_base import TaskingEngine
    from ..tasking.rewards import Reward


@dataclass
class RewardCalcSubmission:

    estimate_id: int
    """Unique identifier of the :class:`.EstimateAgent` to calculate reward for."""

    reward: Reward
    """Function used to calculate a sensor/estimate pair's reward."""

    sensor_list: list[int]
    """Unique identifiers of the sensors task-able by the calling tasking engine."""


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
    estimate_store = getEstimateStore()
    estimate = ray.get(estimate_store.getAgent.remote(submission.estimate_id))

    # Ensure the visibility and metric matrices are the same scale as in the tasking engine
    visibility = zeros(len(submission.sensor_list), dtype=bool)
    metric_matrix = zeros((len(submission.sensor_list), len(submission.reward.metrics)), dtype=float)

    sensor_store = getSensorStore()
    for sensor_index, sensor_id in enumerate(submission.sensor_list):
        sensor_agent = ray.get(sensor_store.getAgent.remote(sensor_id))

        # Attempt predicted observations, in order to perform sensor tasking
        # Only calculate metrics if the estimate is observable
        if predicted_observation := predictObservation(sensor_agent, estimate):
            # This is required to update the metrics attached to the UKF/KF for this observation
            estimate.nominal_filter.forecast([predicted_observation])
            visibility[sensor_index] = True
            metric_matrix[sensor_index] = submission.reward.calculateMetrics(estimate, sensor_agent)

    return RewardCalcResult(
        estimate_id=submission.estimate_id,
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
        return RewardCalcSubmission(
            estimate_id=self._estimate_id,
            reward=self._registrant.reward,
            sensor_list=self._registrant.sensor_list
        )

    def processResults(self, results: RewardCalcResult):
        """Update the :attr:`._registrant`'s visibility and metric matrices."""
        row = self._registrant.target_list.index(results.estimate_id)
        self._registrant.visibility_matrix[row] = results.visibility
        self._registrant.metric_matrix[row] = results.metric_matrix


class TaskingRewardExecutor(JobExecutor):

    @classmethod
    def getRemoteFunc(cls):
        return asyncCalculateReward
