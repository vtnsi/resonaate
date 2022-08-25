"""Defines sensor usage-focused tasking metrics."""
from __future__ import annotations

# Standard Library Imports
from typing import TYPE_CHECKING

# Local Imports
from ...physics import constants as const
from .metric_base import SensorMetric

if TYPE_CHECKING:
    # Local Imports
    from ...agents.estimate_agent import EstimateAgent
    from ...agents.sensing_agent import SensingAgent


class DeltaPosition(SensorMetric):
    """Delta position sensor metric.

    References:
        :cite:t:`nastasi_2018_diss`, Eqn 5.5
    """

    def _calculateMetric(
        self, estimate_agent: EstimateAgent, sensor_agent: SensingAgent, **kwargs
    ) -> float:
        """Calculate the change in angular position required for an observation.

        Args:
            estimate_agent (:class:`.EstimateAgent`): estimate agent for which this metric is being calculated
            sensor_agent (:class:`.SensorAgent`): sensor agent for which this metric is being calculated

        Returns:
            ``float``: Delta boresight metric
        """
        return const.PI - sensor_agent.sensors.delta_boresight


class SlewCycle(SensorMetric):
    """Slew cycle sensor metric."""

    def _calculateMetric(
        self, estimate_agent: EstimateAgent, sensor_agent: SensingAgent, **kwargs
    ) -> float:
        """Calculate the slew frequency for the proposed observation.

        Args:
            estimate_agent (:class:`.EstimateAgent`): estimate agent for which this metric is being calculated
            sensor_agent (:class:`.SensorAgent`): sensor agent for which this metric is being calculated

        Returns:
            ``float``: Slew cycle metric
        """
        return sensor_agent.sensors.slew_rate / sensor_agent.sensors.delta_boresight


class TimeToTransit(SensorMetric):
    """Time-to-transit sensor metric."""

    def __init__(self, norm_factor: float):
        """Create a :class`.TimeToTransit` metric with a normalization factor.

        Args:
            norm_factor (``float``): normalization factor.
        """
        self._norm_factor = norm_factor

    def _calculateMetric(
        self, estimate_agent: EstimateAgent, sensor_agent: SensingAgent, **kwargs
    ) -> float:
        """Calculate the time to slew the sensor from the current position to the proposed observation.

        References:
            :cite:t:`nastasi_2018_diss`, Eqn 5.11 - 5.12

        Args:
            estimate_agent (:class:`.EstimateAgent`): estimate agent for which this metric is being calculated
            sensor_agent (:class:`.SensorAgent`): sensor agent for which this metric is being calculated

        Returns:
            ``float``: Time to transit metric
        """
        return (
            sensor_agent.sensors.delta_boresight / sensor_agent.sensors.slew_rate
        ) / self._norm_factor
