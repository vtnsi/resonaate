"""Abstract :class:`.Reward` base class defining the reward API."""
from __future__ import annotations

# Standard Library Imports
from abc import ABCMeta, abstractmethod
from typing import TYPE_CHECKING

# Local Imports
from ..metrics.metric_base import Metric

if TYPE_CHECKING:
    # Third Party Imports
    from numpy import ndarray

    # Local Imports
    from ...agents.estimate_agent import EstimateAgent
    from ...agents.sensing_agent import SensingAgent


class Reward(metaclass=ABCMeta):
    """Abstract base class to encapsulate behavior of general reward methods."""

    REGISTRY: dict[str, "Reward"] = {}
    """``dict``: Global reward object registry."""

    def __init__(self, metrics: list[Metric]):
        """Construct a reward object with a set of metrics.

        Args:
            metrics (``list``): :class:`.Metric` objects to include in the reward calculation

        Raises:
            TypeError: raised if invalid :class:`.Metric` objects are passed
        """
        if isinstance(metrics, Metric):
            metrics = [metrics]
        if not all(isinstance(metric, Metric) for metric in metrics):
            raise TypeError("Reward constructor must be given Metric objects.")
        self._metrics = metrics

    @classmethod
    def register(cls, name: str, reward: "Reward") -> None:
        """Register an implemented reward class in the global registry.

        Args:
            name (``str``): name to store as the key in the registry
            reward (:class:`.Reward`): reward object to register

        Raises:
            TypeError: raised if not providing a valid :class:`.Reward` sub-class
        """
        if not issubclass(reward, Reward):
            raise TypeError(type(reward))
        cls.REGISTRY[name] = reward

    @property
    def is_registered(self) -> bool:
        """bool: return if an implemented reward class is registered."""
        return self.__class__.__name__ in self.REGISTRY

    def calculateMetrics(
        self, estimate_agent: EstimateAgent, sensor_agent: SensingAgent, **kwargs
    ) -> dict[Metric, float]:
        """Calculate each metric and saves to a dictionary.

        Args:
            estimate_agent (:class:`.EstimateAgent`): estimate agent for which this metric is being calculated
            sensor_agent (:class:`.SensorAgent`): sensor agent for which this metric is being calculated

        Returns:
            (``dict``): calculated metrics for the current simulation state
        """
        metric_solutions = {}
        for metric in self.metrics:
            metric_solutions[metric] = metric(estimate_agent, sensor_agent, **kwargs)

        return metric_solutions

    @abstractmethod
    def _calculateReward(
        self, estimate_agent: EstimateAgent, sensor_agent: SensingAgent, **kwargs
    ) -> ndarray:
        """Abstract function for calculating rewards based on the simulation state.

        Note:
            Must be overridden by implementors.

        Args:
            estimate_agent (:class:`.EstimateAgent`): estimate agent for which this metric is being calculated
            sensor_agent (:class:`.SensorAgent`): sensor agent for which this metric is being calculated

        Returns:
            ``ndarray``: calculated reward
        """
        raise NotImplementedError

    def __call__(
        self, estimate_agent: EstimateAgent, sensor_agent: SensingAgent, **kwargs
    ) -> ndarray:
        """Call operator '()' for reward objects.

        Args:
            estimate_agent (:class:`.EstimateAgent`): estimate agent for which this metric is being calculated
            sensor_agent (:class:`.SensorAgent`): sensor agent for which this metric is being calculated

        Returns:
            ``ndarray``: calculated reward
        """
        return self._calculateReward(estimate_agent, sensor_agent, **kwargs)

    @property
    def metrics(self) -> list[Metric]:
        """``list``: metric objects used to calculate the reward."""
        return self._metrics
