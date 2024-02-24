"""Defines stability-focused tasking metrics."""

from __future__ import annotations

# Standard Library Imports
from typing import TYPE_CHECKING

# Third Party Imports
from numpy import log2, sqrt, trace

# Local Imports
from .metric_base import StabilityMetric

if TYPE_CHECKING:
    # Local Imports
    from ...agents.estimate_agent import EstimateAgent
    from ...agents.sensing_agent import SensingAgent


class LyapunovStability(StabilityMetric):
    """Lyapunov stability metric."""

    def calculate(self, estimate_agent: EstimateAgent, sensor_agent: SensingAgent) -> float:
        """Calculate the scalar maximal Lyapunov exponent approximation.

        References:
            :cite:t:`nastasi_2018_diss`, Section 2.5.3

        Args:
            estimate_agent (:class:`.EstimateAgent`): estimate agent for which this metric is being calculated
            sensor_agent (:class:`.SensorAgent`): sensor agent for which this metric is being calculated

        Returns:
            ``float``: Lyapunov exponent metric
        """
        time = estimate_agent.nominal_filter.time
        predicted_covar = estimate_agent.nominal_filter.pred_p
        initial_covariance = estimate_agent.initial_covariance
        ## [REVIEW][UKF-Numeric] This is a work-around because P <= 0 is possible.
        return (1.0 / time) * log2(sqrt(abs(trace(predicted_covar) / trace(initial_covariance))))
