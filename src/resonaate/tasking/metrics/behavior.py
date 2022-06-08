# Standard Library Imports
# Third Party Imports
# RESONAATE Imports
from .metric_base import BehaviorMetric


class TimeSinceObservation(BehaviorMetric):
    """Time since observation behavior metric."""

    def _calculateMetric(self, target_agents, target_id, sensor_agents, sensor_id, **kwargs):
        """Calculate the total minutes since the last observation of this target.

        Args:
            current_time (float): julian date of current time step
            observation_time (float): julian date of last time step with an observation

        Returns:
            (float): Time since last observation in minutes
        """
        current_time = target_agents[target_id].julian_date_epoch
        observation_time = target_agents[target_id].last_observed_at
        return float((current_time - observation_time) * 24 * 60)
