"""Defines information-focused tasking metrics."""

from __future__ import annotations

# Standard Library Imports
from typing import TYPE_CHECKING

# Third Party Imports
from numpy import trace
from numpy.linalg import eigvals
from scipy.linalg import det

# Local Imports
from .metric_base import UncertaintyMetric

if TYPE_CHECKING:
    # Local Imports
    from ...agents.estimate_agent import EstimateAgent
    from ...agents.sensing_agent import SensingAgent

# ruff: noqa: ARG002


class PositionCovarianceTrace(UncertaintyMetric):
    """Trace of the position covariance metric."""

    def calculate(
        self,
        estimate_agent: EstimateAgent,
        sensor_agent: SensingAgent,
    ):
        """Calculate the Trace of the position covariance.

        Args:
            estimate_agent (:class:`.EstimateAgent`): estimate agent for which this metric is being calculated
            sensor_agent (:class:`.SensorAgent`): sensor agent for which this metric is being calculated

        Returns:
            (``float``): Trace of the position covariance.
        """
        predicted_covar = estimate_agent.nominal_filter.pred_p
        return trace(predicted_covar[:3, :3])


class VelocityCovarianceTrace(UncertaintyMetric):
    """Trace of the velocity covariance metric."""

    def calculate(
        self,
        estimate_agent: EstimateAgent,
        sensor_agent: SensingAgent,
    ):
        """Calculate the Trace of the velocity covariance metric.

        Args:
            estimate_agent (:class:`.EstimateAgent`): estimate agent for which this metric is being calculated
            sensor_agent (:class:`.SensorAgent`): sensor agent for which this metric is being calculated

        Returns:
            (``float``): Trace of the velocity covariance.
        """
        predicted_covar = estimate_agent.nominal_filter.pred_p
        return trace(predicted_covar[3:, 3:])


class PositionCovarianceDeterminant(UncertaintyMetric):
    """Determinant of the position covariance metric."""

    def calculate(
        self,
        estimate_agent: EstimateAgent,
        sensor_agent: SensingAgent,
    ):
        """Calculate the Determinant of the position covariance.

        Args:
            estimate_agent (:class:`.EstimateAgent`): estimate agent for which this metric is being calculated
            sensor_agent (:class:`.SensorAgent`): sensor agent for which this metric is being calculated

        Returns:
            (``float``): Determinant of the position covariance.
        """
        predicted_covar = estimate_agent.nominal_filter.pred_p
        return det(predicted_covar[:3, :3])


class VelocityCovarianceDeterminant(UncertaintyMetric):
    """Determinant of the velocity covariance metric."""

    def calculate(
        self,
        estimate_agent: EstimateAgent,
        sensor_agent: SensingAgent,
    ):
        """Calculate the Determinant of the velocity covariance.

        Args:
            estimate_agent (:class:`.EstimateAgent`): estimate agent for which this metric is being calculated
            sensor_agent (:class:`.SensorAgent`): sensor agent for which this metric is being calculated

        Returns:
            (``float``): Determinant of the velocity covariance.
        """
        predicted_covar = estimate_agent.nominal_filter.pred_p
        return det(predicted_covar[3:, 3:])


class PositionMaxEigenValue(UncertaintyMetric):
    """Max eigenvalue of the position covariance metric."""

    def calculate(
        self,
        estimate_agent: EstimateAgent,
        sensor_agent: SensingAgent,
    ):
        """Calculate the Max eigenvalue of the position covariance.

        Args:
            estimate_agent (:class:`.EstimateAgent`): estimate agent for which this metric is being calculated
            sensor_agent (:class:`.SensorAgent`): sensor agent for which this metric is being calculated

        Returns:
            (``float``): Max eigenvalue of the position covariance.
        """
        predicted_covar = estimate_agent.nominal_filter.pred_p
        return max(eigvals(predicted_covar[:3, :3]))


class VelocityMaxEigenValue(UncertaintyMetric):
    """Max eigenvalue of the velocity covariance metric."""

    def calculate(
        self,
        estimate_agent: EstimateAgent,
        sensor_agent: SensingAgent,
    ):
        """Calculate the Max eigenvalue of the velocity covariance.

        Args:
            estimate_agent (:class:`.EstimateAgent`): estimate agent for which this metric is being calculated
            sensor_agent (:class:`.SensorAgent`): sensor agent for which this metric is being calculated

        Returns:
            (``float``): Max eigenvalue of the velocity covariance.
        """
        predicted_covar = estimate_agent.nominal_filter.pred_p
        return max(eigvals(predicted_covar[3:, 3:]))


class PositionCovarianceReduction(UncertaintyMetric):
    """Position Covariance Reduction metric."""

    def calculate(
        self,
        estimate_agent: EstimateAgent,
        sensor_agent: SensingAgent,
    ):
        """Calculate the trace of the Position Covariance Reduction.

        Args:
            estimate_agent (:class:`.EstimateAgent`): estimate agent for which this metric is being calculated
            sensor_agent (:class:`.SensorAgent`): sensor agent for which this metric is being calculated

        Returns:
            (``float``): Trace of the Position Covariance Reduction metric.
        """
        predicted_covar = estimate_agent.nominal_filter.pred_p
        estimated_covar = estimate_agent.nominal_filter.est_p
        return trace(predicted_covar[:3, :3] - estimated_covar[:3, :3])


class VelocityCovarianceReduction(UncertaintyMetric):
    """Velocity Covariance Reduction metric."""

    def calculate(
        self,
        estimate_agent: EstimateAgent,
        sensor_agent: SensingAgent,
    ):
        """Calculate the trace of the Velocity Covariance Reduction.

        Args:
            estimate_agent (:class:`.EstimateAgent`): estimate agent for which this metric is being calculated
            sensor_agent (:class:`.SensorAgent`): sensor agent for which this metric is being calculated

        Returns:
            (``float``): Trace of the Velocity Covariance Reduction metric.
        """
        predicted_covar = estimate_agent.nominal_filter.pred_p
        estimated_covar = estimate_agent.nominal_filter.est_p
        return trace(predicted_covar[3:, 3:] - estimated_covar[3:, 3:])
