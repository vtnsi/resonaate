"""Defines target-focused tasking metrics."""

from __future__ import annotations

# Standard Library Imports
from typing import TYPE_CHECKING

# Local Imports
from ...physics.constants import DAYS2SEC
from .metric_base import TargetMetric

if TYPE_CHECKING:
    # Local Imports
    from ...agents.estimate_agent import EstimateAgent
    from ...agents.sensing_agent import SensingAgent


class TimeSinceObservation(TargetMetric):
    """Time since observation target metric."""

    def calculate(self, estimate_agent: EstimateAgent, sensor_agent: SensingAgent) -> float:
        """Calculate the total seconds since the last observation of this target.

        Args:
            estimate_agent (:class:`.EstimateAgent`): estimate agent for which this metric is being calculated
            sensor_agent (:class:`.SensorAgent`): sensor agent for which this metric is being calculated

        Returns:
            ``float``: Time since last observation in seconds
        """
        current_time = estimate_agent.julian_date_epoch
        observation_time = estimate_agent.last_observed_at
        return float((current_time - observation_time) * DAYS2SEC)
