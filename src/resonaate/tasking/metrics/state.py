"""Defines state-focused tasking metrics."""

from __future__ import annotations

# Standard Library Imports
from typing import TYPE_CHECKING

# Third Party Imports
from scipy.linalg import norm

# Local Imports
from .metric_base import StateMetric

if TYPE_CHECKING:
    # Local Imports
    from ...agents.estimate_agent import EstimateAgent
    from ...agents.sensing_agent import SensingAgent


class Range(StateMetric):
    """Range state metric."""

    def calculate(self, estimate_agent: EstimateAgent, sensor_agent: SensingAgent) -> float:
        """Calculate the range this target.

        Args:
            estimate_agent (:class:`.EstimateAgent`): estimate agent for which this metric is being calculated
            sensor_agent (:class:`.SensorAgent`): sensor agent for which this metric is being calculated

        Returns:
            ``float``: estimated range to target
        """
        target_position = estimate_agent.eci_state[:3]
        sensor_position = sensor_agent.eci_state[:3]
        return norm(target_position - sensor_position)
