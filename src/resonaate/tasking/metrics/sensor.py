"""Defines sensor usage-focused tasking metrics."""
from __future__ import annotations

# Standard Library Imports
from typing import TYPE_CHECKING

# Local Imports
from ...physics import constants as const
from ...physics.transforms.methods import getSlantRangeVector
from .metric_base import SensorMetric

if TYPE_CHECKING:
    # Local Imports
    from ...agents.estimate_agent import EstimateAgent
    from ...agents.sensing_agent import SensingAgent


def _getDeltaBoresight(estimate_agent: EstimateAgent, sensor_agent: SensingAgent) -> float:
    """Shortcut to calculate the angular separation of an `estimate_agent` from a `sensor_agent` boresight.

    Args:
        estimate_agent (EstimateAgent): agent whose position is used to measure separation from boresight
        sensor_agent (SensingAgent): sensor whose boresight is used to measure separation

    Returns:
        float: angular separation between `estimate_agent` position and sensor boresight (radians)
    """
    slant_range_sez = getSlantRangeVector(
        sensor_agent.eci_state, estimate_agent.eci_state, sensor_agent.datetime_epoch
    )
    return sensor_agent.sensors.deltaBoresight(slant_range_sez[:3])


class DeltaPosition(SensorMetric):
    """Delta position sensor metric.

    References:
        :cite:t:`nastasi_2018_diss`, Eqn 5.5
    """

    def calculate(
        self,
        estimate_agent: EstimateAgent,
        sensor_agent: SensingAgent,
    ) -> float:
        """Calculate the change in angular position required for an observation.

        Args:
            estimate_agent (:class:`.EstimateAgent`): estimate agent for which this metric is being calculated
            sensor_agent (:class:`.SensorAgent`): sensor agent for which this metric is being calculated

        Returns:
            ``float``: Delta boresight metric
        """
        delta_boresight = _getDeltaBoresight(estimate_agent, sensor_agent)
        return const.PI - delta_boresight


class SlewCycle(SensorMetric):
    """Slew cycle sensor metric."""

    def calculate(
        self,
        estimate_agent: EstimateAgent,
        sensor_agent: SensingAgent,
    ) -> float:
        """Calculate the slew frequency for the proposed observation.

        Args:
            estimate_agent (:class:`.EstimateAgent`): estimate agent for which this metric is being calculated
            sensor_agent (:class:`.SensorAgent`): sensor agent for which this metric is being calculated

        Returns:
            ``float``: Slew cycle metric
        """
        delta_boresight = _getDeltaBoresight(estimate_agent, sensor_agent)
        return sensor_agent.sensors.slew_rate / delta_boresight


class TimeToTransit(SensorMetric):
    """Time-to-transit sensor metric.

    References:
        :cite:t:`nastasi_2018_diss`, Eqn 5.11 - 5.12
    """

    def __init__(self, norm_factor: float):
        """Create a :class`.TimeToTransit` metric with a normalization factor.

        Args:
            norm_factor (``float``): normalization factor.
        """
        self._norm_factor = norm_factor

    def calculate(
        self,
        estimate_agent: EstimateAgent,
        sensor_agent: SensingAgent,
    ) -> float:
        """Calculate the time to slew the sensor from the current position to the proposed observation.

        Args:
            estimate_agent (:class:`.EstimateAgent`): estimate agent for which this metric is being calculated
            sensor_agent (:class:`.SensorAgent`): sensor agent for which this metric is being calculated

        Returns:
            ``float``: Time to transit metric
        """
        delta_boresight = _getDeltaBoresight(estimate_agent, sensor_agent)
        return (delta_boresight / sensor_agent.sensors.slew_rate) / self._norm_factor
