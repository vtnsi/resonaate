# Standard Library Imports
import logging
# Third Party Imports
from numpy import log, matmul
from numpy.linalg import LinAlgError
from scipy.linalg import det, inv
# RESONAATE Imports
from .metric_base import InformationMetric


class FisherInformation(InformationMetric):
    """Fisher information metric."""

    def _calculateMetric(self, target_agents, target_id, sensor_agents, sensor_id, **kwargs):
        """Calculate the determinant of the Fisher information gain.

        Args:
            cross_covar (``numpy.ndarray``): UKF cross-covariance
            predicted_covar (``numpy.ndarray``): UKF a priori covariance
            r_matrix (``numpy.ndarray``): measurement noise covariance of sensor
            filter_type (str): the type of filter used

        Returns:
            (float): Fisher information gain metric.
        """
        cross_covar = target_agents[target_id].nominal_filter.cross_cvr
        predicted_covar = target_agents[target_id].nominal_filter.pred_p
        r_matrix = sensor_agents[sensor_id].sensors.r_matrix

        try:
            nu_var = matmul(cross_covar.T, inv(predicted_covar))
            fisher_info_gain = matmul(matmul(nu_var.T, inv(r_matrix)), nu_var)
        except LinAlgError:
            msg = "Singular matrix in Fisher metric.\nPred Covar: {0}\nMeas Noise: {1}"
            logger = logging.getLogger("resonaate")
            logger.error(msg.format(predicted_covar, r_matrix))
            raise

        return abs(det(fisher_info_gain))


class ShannonInformation(InformationMetric):
    """Shannon information metric."""

    def _calculateMetric(self, target_agents, target_id, sensor_agents, sensor_id, **kwargs):
        """Calculate the log of the Shannon Information gain.

        Args:
            predicted_covar (``numpy.ndarray``): UKF a priori covariance
            estimated_covar (``numpy.ndarray``): UKF a posteriori covariance

        Returns:
            (float): Shannon information gain metric.
        """
        predicted_covar = target_agents[target_id].nominal_filter.pred_p
        estimated_covar = target_agents[target_id].nominal_filter.est_p
        shannon_info = 0.5 * log(det(predicted_covar) / det(estimated_covar))

        return shannon_info


class KLDivergence(InformationMetric):
    """Kullback-Leibler Divergence metric."""

    def _calculateMetric(self, target_agents, target_id, sensor_agents, sensor_id, **kwargs):
        """Calculate the Kullback-Leibler Divergence.

        Args:
            predicted_covar (``numpy.ndarray``): UKF a priori covariance
            estimated_covar (``numpy.ndarray``): UKF a posteriori covariance

        Returns:
            (float): Kullback-Leibler Divergence metric.
        """
        predicted_covar = target_agents[target_id].nominal_filter.pred_p
        estimated_covar = target_agents[target_id].nominal_filter.est_p
        kld = det(predicted_covar) * log(det(predicted_covar) / det(estimated_covar))

        return kld
