"""Defines sensor usage-focused tasking metrics."""
# Local Imports
from ...physics import constants as const
from .metric_base import SensorMetric


class DeltaPosition(SensorMetric):
    """Delta position sensor metric.

    References:
        :cite:t:`nastasi_2018_diss`, Eqn 5.5
    """

    def _calculateMetric(self, target_agents, target_id, sensor_agents, sensor_id, **kwargs):
        """Calculate the change in angular position required for an observation.

        Args:
            delta_boresight (float): required change of boresight vector in radians

        Returns:
            (float): Delta boresight metric
        """
        return const.PI - sensor_agents[sensor_id].sensors.delta_boresight


class SlewCycle(SensorMetric):
    """Slew cycle sensor metric."""

    def _calculateMetric(self, target_agents, target_id, sensor_agents, sensor_id, **kwargs):
        """Calculate the slew frequency for the proposed observation.

        Args:
            slew_rate (float): the sensor's maximum slew rate
            delta_boresight (float): required change of boresight vector in radians

        Returns:
            (float): Slew cycle metric
        """
        return (
            sensor_agents[sensor_id].sensors.slew_rate
            / sensor_agents[sensor_id].sensors.delta_boresight
        )


class TimeToTransit(SensorMetric):
    """Time-to-transit sensor metric."""

    def __init__(self, norm_factor):
        """Override init to set the normalization factor."""
        self._norm_factor = norm_factor

    def _calculateMetric(self, target_agents, target_id, sensor_agents, sensor_id, **kwargs):
        """Calculate the time to slew the sensor from the current position to the proposed observation.

        References:
            :cite:t:`nastasi_2018_diss`, Eqn 5.11 - 5.12

        Args:
            delta_boresight (float): required change of boresight vector in radians
            slew_rate (float): the sensor's maximum slew rate
            norm_factor (float): a factor to normalize the time to transit

        Returns:
            (float): Time to transit metric
        """
        return (
            sensor_agents[sensor_id].sensors.delta_boresight
            / sensor_agents[sensor_id].sensors.slew_rate
        ) / self._norm_factor
