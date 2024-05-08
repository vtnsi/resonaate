"""Defines sensor usage-focused tasking metrics."""

from __future__ import annotations

# Standard Library Imports
from typing import TYPE_CHECKING

# Local Imports
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
        sensor_agent.eci_state,
        estimate_agent.eci_state,
        sensor_agent.datetime_epoch,
    )
    return sensor_agent.sensors.deltaBoresight(slant_range_sez[:3])


class SlewDistanceMaximization(SensorMetric):
    """Slew Distance Maximization sensor metric.

    References:
        :cite:t:`nastasi_2018_diss`, Eqn 5.5
    """

    def calculate(
        self,
        estimate_agent: EstimateAgent,
        sensor_agent: SensingAgent,
    ) -> float:
        """Calculate the distance in angular position required for an observation.

        Args:
            estimate_agent (:class:`.EstimateAgent`): estimate agent for which this metric is being calculated
            sensor_agent (:class:`.SensorAgent`): sensor agent for which this metric is being calculated

        Returns:
            ``float``: Slew Distance Maximization metric
        """
        return _getDeltaBoresight(estimate_agent, sensor_agent)


class SlewDistanceMinimization(SensorMetric):
    """Slew Distance Minimization sensor metric.

    References:
        :cite:t:`nastasi_2018_diss`, Eqn 5.5
    """

    def calculate(
        self,
        estimate_agent: EstimateAgent,
        sensor_agent: SensingAgent,
    ) -> float:
        """Calculate the reciprocal length in angular position required for an observation.

        Args:
            estimate_agent (:class:`.EstimateAgent`): estimate agent for which this metric is being calculated
            sensor_agent (:class:`.SensorAgent`): sensor agent for which this metric is being calculated

        Returns:
            ``float``: Slew Distance Minimization metric
        """
        delta_boresight = _getDeltaBoresight(estimate_agent, sensor_agent)
        return 1 / delta_boresight


class SlewTimeMinimization(SensorMetric):
    """Minimum slew time sensor metric."""

    def calculate(
        self,
        estimate_agent: EstimateAgent,
        sensor_agent: SensingAgent,
    ) -> float:
        """Calculate the frequency to slew the sensor from the current position to the proposed observation, in seconds.

        Args:
            estimate_agent (:class:`.EstimateAgent`): estimate agent for which this metric is being calculated
            sensor_agent (:class:`.SensorAgent`): sensor agent for which this metric is being calculated

        Returns:
            ``float``: Slew minimization metric
        """
        delta_boresight = _getDeltaBoresight(estimate_agent, sensor_agent)
        return sensor_agent.sensors.slew_rate / delta_boresight


class SlewTimeMaximization(SensorMetric):
    """Maximum slew time sensor metric.

    References:
        :cite:t:`nastasi_2018_diss`, Eqn 5.11 - 5.12
    """

    def __init__(self):
        """Create a :class`.SlewTimeMaximization` metric."""

    def calculate(
        self,
        estimate_agent: EstimateAgent,
        sensor_agent: SensingAgent,
    ) -> float:
        """Calculate the time to slew the sensor from the current position to the proposed observation, in seconds.

        Args:
            estimate_agent (:class:`.EstimateAgent`): estimate agent for which this metric is being calculated
            sensor_agent (:class:`.SensorAgent`): sensor agent for which this metric is being calculated

        Returns:
            ``float``: time to slew metric
        """
        delta_boresight = _getDeltaBoresight(estimate_agent, sensor_agent)
        return delta_boresight / sensor_agent.sensors.slew_rate
