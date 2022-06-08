# Standard Library Imports
# Third Party Imports
from numpy import log2, trace, sqrt
# RESONAATE Imports
from .metric_base import StabilityMetric


class LyapunovStability(StabilityMetric):
    """Lyapunov stability metric."""

    def _calculateMetric(self, target_agents, target_id, sensor_agents, sensor_id, **kwargs):
        """Calculate the scalar maximal Lyapunov exponent approximation.

        Args:
            time (float): current time in epoch seconds
            predicted_covar (``numpy.ndarray``): UKF a priori covariance
            initial_covariance (``numpy.ndarray``): original error covariance

        Returns:
            (float): Lyapunov exponent metric
        """
        time = target_agents[target_id].nominal_filter.time
        predicted_covar = target_agents[target_id].nominal_filter.pred_p
        initial_covariance = target_agents[target_id].initial_covariance
        ## [REVIEW][UKF-Numeric] This is a work-around because P <= 0 is possible.
        return (1.0 / time) * log2(sqrt(abs(trace(predicted_covar) / trace(initial_covariance))))
