"""Abstract :class:`.Metric` base class defining the metric API."""

from __future__ import annotations

# Standard Library Imports
from abc import ABCMeta, abstractmethod
from typing import TYPE_CHECKING

# Local Imports
from ...common.labels import MetricTypeLabel

if TYPE_CHECKING:

    # Local Imports
    from ...agents.estimate_agent import EstimateAgent
    from ...agents.sensing_agent import SensingAgent


class Metric(metaclass=ABCMeta):
    """Abstract base class to encapsulate behavior of general metrics."""

    METRIC_TYPE: str = "base"
    """``str``: Type of metric in str format, for reward logic."""

    @abstractmethod
    def calculate(
        self,
        estimate_agent: EstimateAgent,
        sensor_agent: SensingAgent,
    ) -> float:
        """Abstract function for calculating the metric based on the set of targets & sensors.

        Note:
            Must be overridden by implementors.

        Args:
            estimate_agent (:class:`.EstimateAgent`): estimate agent for which this metric is being calculated
            sensor_agent (:class:`.SensorAgent`): sensor agent for which this metric is being calculated

        Returns:
            ``float``: single, target-sensor paired metric value
        """
        raise NotImplementedError

    @property
    def metric_type(self) -> str:
        """``str``: return the type of metric in str format, for convenience."""
        return self.METRIC_TYPE


class InformationMetric(Metric):
    """Information metric type base class.

    These metrics should quantify the information from predicted observations/estimates.
    These prioritize pure estimation performance. These consist of information gain equations.
    """

    METRIC_TYPE: str = MetricTypeLabel.INFORMATION
    """``str``: Type of metric in str format, for reward logic."""

    @abstractmethod
    def calculate(self, estimate_agent: EstimateAgent, sensor_agent: SensingAgent) -> float:
        """Define logic for calculating metrics based on the given target/sensor sets.

        Must be overridden by implementors.
        """
        raise NotImplementedError


class UncertaintyMetric(Metric):
    """Uncertainty metric type base class.

    These metrics should quantify the uncertainty reduction from predicted observations/estimates.
    These prioritize uncertainty reduction. These are operations directly on the covariance.
    """

    METRIC_TYPE: str = MetricTypeLabel.UNCERTAINTY

    @abstractmethod
    def calculate(self, estimate_agent: EstimateAgent, sensor_agent: SensingAgent) -> float:
        """Define logic for calculating metrics based on the given target/sensor sets.

        Must be overridden by implementors.
        """
        raise NotImplementedError


class StabilityMetric(Metric):
    """Stability metric type base class.

    These metrics quantify the stability of an estimate, and limit observations for
    well-estimated/observed targets.
    """

    METRIC_TYPE: str = MetricTypeLabel.STABILITY
    """``str``: Type of metric in str format, for reward logic."""

    @abstractmethod
    def calculate(
        self,
        estimate_agent: EstimateAgent,
        sensor_agent: SensingAgent,
    ) -> float:
        """Define logic for calculating metrics based on the given target/sensor sets.

        Must be overridden by implementors.
        """
        raise NotImplementedError


class SensorMetric(Metric):
    """Sensor metric type base class.

    These metrics quantify the impact of observations on the actual sensor agent, and
    limit "costly" collections.
    """

    METRIC_TYPE: str = MetricTypeLabel.SENSOR
    """``str``: Type of metric in str format, for reward logic."""

    @abstractmethod
    def calculate(
        self,
        estimate_agent: EstimateAgent,
        sensor_agent: SensingAgent,
    ) -> float:
        """Define logic for calculating metrics based on the given target/sensor sets.

        Must be overridden by implementors.
        """
        raise NotImplementedError


class TargetMetric(Metric):
    """Target metric type base class.

    These metrics quantify the impact of observations on the actual target agent. They focus on
    the recency of the last observation, tasking priority, and orbital regime.
    """

    METRIC_TYPE: str = MetricTypeLabel.TARGET
    """``str``: Type of metric in str format, for reward logic."""

    @abstractmethod
    def calculate(
        self,
        estimate_agent: EstimateAgent,
        sensor_agent: SensingAgent,
    ) -> float:
        """Define logic for calculating metrics based on the given target/sensor sets.

        Must be overridden by implementors.
        """
        raise NotImplementedError


class StateMetric(Metric):
    """State metric type base class.

    These metrics quantify the state of a target, and limit observations based on orientation,
    background lighting, attitude, and range.
    """

    METRIC_TYPE: str = MetricTypeLabel.STATE

    @abstractmethod
    def calculate(
        self,
        estimate_agent: EstimateAgent,
        sensor_agent: SensingAgent,
    ) -> float:
        """Define logic for calculating metrics based on the given target/sensor sets.

        Must be overridden by implementors.
        """
        raise NotImplementedError
