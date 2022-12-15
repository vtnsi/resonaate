"""Define implemented reward functions used to evaluate sensor task opportunities."""
from __future__ import annotations

# Standard Library Imports
from typing import TYPE_CHECKING

# Third Party Imports
from numpy import sign
from numpy import sum as np_sum

# Local Imports
from ..metrics.metric_base import (
    INFORMATION_METRIC_LABEL,
    SENSOR_METRIC_LABEL,
    STABILITY_METRIC_LABEL,
    TARGET_METRIC_LABEL,
)
from .reward_base import Reward

if TYPE_CHECKING:
    # Third Party Imports
    from numpy import ndarray

    # Local Imports
    from ..metrics.metric_base import Metric


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
            metrics (``list``): :class:`.Metric` instances for calculating the reward
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
            if metric.metric_type == STABILITY_METRIC_LABEL:
                stability = True
            if metric.metric_type == INFORMATION_METRIC_LABEL:
                information = True
            if metric.metric_type == SENSOR_METRIC_LABEL:
                sensor = True

        if not all([stability, information, sensor]):
            raise TypeError("Incorrect assignment of metrics")

    def calculate(self, metric_matrix: ndarray) -> float:
        """Calculate the cost-constrained reward.

        Note:
            This implements the following equation:
                r = delta * (sign(stab) + info) - (1 - delta) * sens

        Args:
            metric_matrix (``ndarray``): 2D array of metrics

        Returns:
            ``float``: Cost constrained reward
        """
        stability = metric_matrix[..., self._metric_type_indices[STABILITY_METRIC_LABEL]].squeeze()
        information = metric_matrix[
            ..., self._metric_type_indices[INFORMATION_METRIC_LABEL]
        ].squeeze()
        sensor = metric_matrix[..., self._metric_type_indices[SENSOR_METRIC_LABEL]].squeeze()

        return self._delta * (sign(stability) + information) - (1 - self._delta) * sensor


class SimpleSummationReward(Reward):
    """Simple summation reward function.

    This function takes any range of metrics, and sums them all together.
    """

    def calculate(self, metric_matrix: ndarray) -> float:
        """Calculate the reward as the direct sum of each metric.

        References:
            :cite:t:`kadan_2021_scitech_parametric`

        Args:
            metric_matrix (``ndarray``): 2D array of metrics

        Returns:
            ``float``: Summation reward
        """
        return np_sum(metric_matrix, axis=2)


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
            metrics (``list``): :class:`.Metric` instances for calculating the reward
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
            if metric.metric_type == STABILITY_METRIC_LABEL:
                stability = True
            if metric.metric_type == INFORMATION_METRIC_LABEL:
                information = True
            if metric.metric_type == SENSOR_METRIC_LABEL:
                sensor = True
            if metric.metric_type == TARGET_METRIC_LABEL:
                behavior = True

        if not all([stability, information, sensor, behavior]):
            raise TypeError("Incorrect assignment of metrics")

    def calculate(self, metric_matrix: ndarray) -> float:
        """Calculate the Combined cost-constrained staleness reward.

        References:
            :cite:t:`kadan_2021_scitech_parametric`

        Note:
            This implements the following equation:
                r = delta * (sign(stab) + info) - (1 - delta) * sens + staleness

        Args:
            metric_matrix (``ndarray``): 2D array of metrics

        Returns:
            ``float``: Combined reward
        """
        stability = metric_matrix[..., self._metric_type_indices[STABILITY_METRIC_LABEL]].squeeze()
        information = metric_matrix[
            ..., self._metric_type_indices[INFORMATION_METRIC_LABEL]
        ].squeeze()
        sensor = metric_matrix[..., self._metric_type_indices[SENSOR_METRIC_LABEL]].squeeze()
        behavior = metric_matrix[..., self._metric_type_indices[TARGET_METRIC_LABEL]].squeeze()

        return (
            self._delta * (sign(stability) + information) - (1 - self._delta) * sensor
        ) + behavior
