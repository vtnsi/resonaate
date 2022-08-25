"""Defines behavior-focused tasking metrics."""
from __future__ import annotations

# Standard Library Imports
from typing import TYPE_CHECKING

# Local Imports
from .metric_base import BehaviorMetric

if TYPE_CHECKING:
    # Local Imports
    from ...agents.estimate_agent import EstimateAgent
    from ...agents.sensing_agent import SensingAgent


class TimeSinceObservation(BehaviorMetric):
    """Time since observation behavior metric."""

    def _calculateMetric(
        self, estimate_agent: EstimateAgent, sensor_agent: SensingAgent, **kwargs
    ) -> float:
        """Calculate the total minutes since the last observation of this target.

        Args:
            estimate_agent (:class:`.EstimateAgent`): estimate agent for which this metric is being calculated
            sensor_agent (:class:`.SensorAgent`): sensor agent for which this metric is being calculated

        Returns:
            ``float``: Time since last observation in minutes
        """
        current_time = estimate_agent.julian_date_epoch
        observation_time = estimate_agent.last_observed_at
        return float((current_time - observation_time) * 24 * 60)
