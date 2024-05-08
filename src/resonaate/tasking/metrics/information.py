"""Defines information-focused tasking metrics."""

from __future__ import annotations

# Standard Library Imports
from typing import TYPE_CHECKING

# Third Party Imports
from numpy import log, matmul
from numpy.linalg import LinAlgError
from scipy.linalg import det, inv

# Local Imports
from ...common.logger import resonaateLogError
from .metric_base import InformationMetric

if TYPE_CHECKING:
    # Local Imports
    from ...agents.estimate_agent import EstimateAgent
    from ...agents.sensing_agent import SensingAgent


class FisherInformation(InformationMetric):
    """Fisher information metric.

    References:
        #. :cite:t:`bar-shalom_2001_estimation`
        #. :cite:t:`crassidis_2012_optest`
        #. :cite:t:`ristic_2003_fig`
        #. :cite:t:`williams_2012_diss`
    """

    def calculate(
        self,
        estimate_agent: EstimateAgent,
        sensor_agent: SensingAgent,
    ) -> float:
        """Calculate the determinant of the Fisher information gain.

        Args:
            estimate_agent (:class:`.EstimateAgent`): estimate agent for which this metric is being calculated
            sensor_agent (:class:`.SensorAgent`): sensor agent for which this metric is being calculated

        Returns:
            ``float``: Fisher information gain metric.
        """
        cross_covar = estimate_agent.nominal_filter.cross_cvr
        predicted_covar = estimate_agent.nominal_filter.pred_p
        r_matrix = sensor_agent.sensors.r_matrix

        try:
            nu_var = matmul(cross_covar.T, inv(predicted_covar))
            fisher_info_gain = matmul(matmul(nu_var.T, inv(r_matrix)), nu_var)
        except LinAlgError:
            msg = f"Singular matrix in Fisher metric.\nPred Covar: {predicted_covar}\nMeas Noise: {r_matrix}"
            resonaateLogError(msg)
            raise

        return abs(det(fisher_info_gain))


class ShannonInformation(InformationMetric):
    """Shannon information metric.

    References:
        #. :cite:t:`williams_2012_aas_dst`
        #. :cite:t:`williams_2012_diss`
    """

    def calculate(
        self,
        estimate_agent: EstimateAgent,
        sensor_agent: SensingAgent,
    ) -> float:
        """Calculate the log of the Shannon Information gain.

        Args:
            estimate_agent (:class:`.EstimateAgent`): estimate agent for which this metric is being calculated
            sensor_agent (:class:`.SensorAgent`): sensor agent for which this metric is being calculated

        Returns:
            ``float``: Shannon information gain metric.
        """
        predicted_covar = estimate_agent.nominal_filter.pred_p
        estimated_covar = estimate_agent.nominal_filter.est_p
        return 0.5 * log(det(predicted_covar) / det(estimated_covar))


class KLDivergence(InformationMetric):
    """Kullback-Leibler Divergence metric.

    References:
        #. :cite:t:`kullback_jstor_1951_info`
    """

    def calculate(
        self,
        estimate_agent: EstimateAgent,
        sensor_agent: SensingAgent,
    ) -> float:
        """Calculate the Kullback-Leibler Divergence.

        Args:
            estimate_agent (:class:`.EstimateAgent`): estimate agent for which this metric is being calculated
            sensor_agent (:class:`.SensorAgent`): sensor agent for which this metric is being calculated

        Returns:
            ``float``: Kullback-Leibler Divergence metric.
        """
        predicted_covar = estimate_agent.nominal_filter.pred_p
        estimated_covar = estimate_agent.nominal_filter.est_p
        return det(predicted_covar) * log(det(predicted_covar) / det(estimated_covar))
