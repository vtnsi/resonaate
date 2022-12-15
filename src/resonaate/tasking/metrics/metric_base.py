"""Abstract :class:`.Metric` base class defining the metric API."""
from __future__ import annotations

# Standard Library Imports
from abc import ABCMeta, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Local Imports
    from ...agents.estimate_agent import EstimateAgent
    from ...agents.sensing_agent import SensingAgent


# Metric type labels
INFORMATION_METRIC_LABEL = "information"
SENSOR_METRIC_LABEL = "sensor"
STABILITY_METRIC_LABEL = "stability"
STATE_METRIC_LABEL = "state"
TARGET_METRIC_LABEL = "target"
UNCERTAINTY_METRIC_LABEL = "uncertainty"


class Metric(metaclass=ABCMeta):
    """Abstract base class to encapsulate behavior of general metrics."""

    METRIC_TYPE: str = "base"
    """``str``: Type of metric in str format, for reward logic."""

    REGISTRY: dict[str, Metric] = {}
    """``dict``: Global metric object registry."""

    @classmethod
    def register(cls, metric: Metric) -> None:
        """Register an implemented metric class in the global registry.

        Args:
            metric (:class:`.Metric`): metric object to register

        Raises:
            TypeError: raised if not providing a valid :class:`.Metric` sub-class
        """
        if not issubclass(metric, Metric):
            raise TypeError(type(metric))

        cls.REGISTRY[metric.__name__] = metric

    @property
    def is_registered(self) -> bool:
        """``bool``: return if an implemented metric class is registered."""
        return self.__class__.__name__ in self.REGISTRY

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

    METRIC_TYPE: str = INFORMATION_METRIC_LABEL
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

    METRIC_TYPE: str = UNCERTAINTY_METRIC_LABEL

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

    METRIC_TYPE: str = STABILITY_METRIC_LABEL
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

    METRIC_TYPE: str = SENSOR_METRIC_LABEL
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

    METRIC_TYPE: str = TARGET_METRIC_LABEL
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

    METRIC_TYPE: str = STATE_METRIC_LABEL

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
