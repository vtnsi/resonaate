"""Define implemented reward functions used to evaluate sensor task opportunities."""
from __future__ import annotations

# Standard Library Imports
from typing import TYPE_CHECKING

# Third Party Imports
from numpy import sign

# Local Imports
from .reward_base import Reward

if TYPE_CHECKING:
    # Third Party Imports
    from numpy import ndarray

    # Local Imports
    from ...agents.estimate_agent import EstimateAgent
    from ...agents.sensing_agent import SensingAgent
    from ..metrics import Metric


class CostConstrainedReward(Reward):
    """Cost-constrained reward function.

    This function constrains the reward from a information metric by the sign
    of the stability metric, and subtracting the sensor metric.

    References:
        :cite:t:`nastasi_2018_diss`, Section 5.3.3
    """

    def __init__(self, metrics: list[Metric], delta: float = 0.85, **kwargs):
        """Construct a cost-constrained reward function.

        Note:
            This class requires one metric of each of the following types:
                - :class:`.Information`
                - :class:`.Stability`
                - :class:`.Sensor`

        Args:
            metrics (``list``): metrics instances for calculating the reward
            delta (``float``, optional): ratio of information reward to sensor reward.
                Defaults to 0.85.

        Raises:
            ValueError: raised if not supplied three metric objects
            TypeError: raised if not supplied one of each metric type from:
                [:class:`.Stability`, :class:`.Information`, :class:`.Sensor`]
        """
        super().__init__(metrics, **kwargs)
        self._delta = delta
        if len(metrics) != 3:
            raise ValueError("Incorrect number of metrics being passed")
        stability, information, sensor = False, False, False
        for metric in metrics:
            if metric.metric_type == "stability":
                stability = True
            if metric.metric_type == "information":
                information = True
            if metric.metric_type == "sensor":
                sensor = True

        if not all([stability, information, sensor]):
            raise TypeError("Incorrect assignment of metrics")

    def _calculateReward(
        self, estimate_agent: EstimateAgent, sensor_agent: SensingAgent, **kwargs
    ) -> ndarray:
        """Calculate the cost-constrained reward.

        Note:
            This implements the following equation:
                r = delta * (sign(stab) + info) - (1 - delta) * sens

        Args:
            estimate_agent (:class:`.EstimateAgent`): estimate agent for which this metric is being calculated
            sensor_agent (:class:`.SensorAgent`): sensor agent for which this metric is being calculated

        Returns:
            ``ndarray``: calculated reward
        """
        metrics = self.calculateMetrics(estimate_agent, sensor_agent, **kwargs)
        for metric, value in metrics.items():
            if metric.metric_type == "stability":
                stability = value
            if metric.metric_type == "information":
                information = value
            if metric.metric_type == "sensor":
                sensor = value

        return self._delta * (sign(stability) + information) - (1 - self._delta) * sensor


class SimpleSummationReward(Reward):
    """Simple summation reward function.

    This function takes any range of metrics, and sums them all together.
    """

    def _calculateReward(
        self, estimate_agent: EstimateAgent, sensor_agent: SensingAgent, **kwargs
    ) -> ndarray:
        """Calculate the reward as the direct sum of each metric.

        References:
            :cite:t:`kadan_2021_scitech_parametric`

        Args:
            estimate_agent (:class:`.EstimateAgent`): estimate agent for which this metric is being calculated
            sensor_agent (:class:`.SensorAgent`): sensor agent for which this metric is being calculated

        Returns:
            ``ndarray``: summed reward
        """
        return sum(self.calculateMetrics(estimate_agent, sensor_agent, **kwargs).values())


class CombinedReward(Reward):
    """Combined Cost-constrained and staleness reward function.

    This function constrains the reward from a information metric by the sign
    of the stability metric, and subtracting the sensor metric.
    """

    def __init__(self, metrics: list[Metric], delta: float = 0.85, **kwargs):
        """Construct a cost-constrained reward function.

        Note:
            This class requires one metric of each of the following types:
                - :class:`.Information`
                - :class:`.Stability`
                - :class:`.Sensor`
                - :class:`.Behavior`

        Args:
            metrics (``list``): metrics instances for calculating the reward
            delta (``float``, optional): ratio of information reward to sensor reward.
                Defaults to 0.85.

        Raises:
            ValueError: raised if not supplied three metric objects
            TypeError: raised if not supplied one of each metric type from:
                [:class:`.Stability`, :class:`.Information`, :class:`.Sensor`, :class:`.Behavior`]
        """
        super().__init__(metrics, **kwargs)
        self._delta = delta
        if len(metrics) != 4:
            raise ValueError("Incorrect number of metrics being passed")
        stability, information, sensor, behavior = False, False, False, False
        for metric in metrics:
            if metric.metric_type == "stability":
                stability = True
            if metric.metric_type == "information":
                information = True
            if metric.metric_type == "sensor":
                sensor = True
            if metric.metric_type == "behavior":
                behavior = True

        if not all([stability, information, sensor, behavior]):
            raise TypeError("Incorrect assignment of metrics")

    def _calculateReward(
        self, estimate_agent: EstimateAgent, sensor_agent: SensingAgent, **kwargs
    ) -> ndarray:
        """Calculate the Combined cost-constrained staleness reward.

        References:
            :cite:t:`kadan_2021_scitech_parametric`

        Note:
            This implements the following equation:
                r = delta * (sign(stab) + info) - (1 - delta) * sens + staleness

        Args:
            estimate_agent (:class:`.EstimateAgent`): estimate agent for which this metric is being calculated
            sensor_agent (:class:`.SensorAgent`): sensor agent for which this metric is being calculated

        Returns:
            ``ndarray``: calculated reward
        """
        metrics = self.calculateMetrics(estimate_agent, sensor_agent, **kwargs)
        for metric, value in metrics.items():
            if metric.metric_type == "stability":
                stability = value
            if metric.metric_type == "information":
                information = value
            if metric.metric_type == "sensor":
                sensor = value
            if metric.metric_type == "behavior":
                behavior = value

        return (
            self._delta * (sign(stability) + information) - (1 - self._delta) * sensor
        ) + behavior
