"""Abstract :class:`.Reward` base class defining the reward API."""

from __future__ import annotations

# Standard Library Imports
from abc import ABCMeta, abstractmethod
from collections import defaultdict
from collections.abc import Iterable
from typing import TYPE_CHECKING

# Third Party Imports
from numpy import array

# Local Imports
from ..metrics.metric_base import Metric

if TYPE_CHECKING:
    # Standard Library Imports
    from typing import ClassVar

    # Third Party Imports
    from numpy import ndarray

    # Local Imports
    from ...agents.estimate_agent import EstimateAgent
    from ...agents.sensing_agent import SensingAgent
    from ...scenario.config.reward_config import RewardConfig


class Reward(metaclass=ABCMeta):
    """Abstract base class to encapsulate behavior of general reward methods."""

    REGISTRY: ClassVar[dict[str, Reward]] = {}
    """``dict``: Global reward object registry."""

    def __init__(self, metrics: list[Metric]):
        """Construct a reward object with a set of metrics.

        Args:
            metrics (``list``): :class:`.Metric` objects to include in the reward calculation

        Raises:
            TypeError: raised if invalid :class:`.Metric` objects are passed
        """
        if isinstance(metrics, Metric):
            # Make metrics a list if there is only one metric
            metrics = [metrics]
        elif not isinstance(metrics, Iterable):
            raise TypeError("Reward constructor must be given Metric objects.")

        if not all(isinstance(metric, Metric) for metric in metrics):
            raise TypeError("Reward constructor must be given Metric objects.")
        self._metrics = metrics

        self._metric_type_indices = defaultdict(list)

        self._metric_class_indices: dict[type[Metric], int] = {}

        for metric in metrics:
            # Fill metric type indexes
            self._metric_type_indices[metric.metric_type].append(metrics.index(metric))

            # Fill metric class indexes
            self._metric_class_indices[metric.__class__] = metrics.index(metric)

    @classmethod
    def fromConfig(cls, metrics: list[Metric], config: RewardConfig) -> Reward:  # noqa: ARG003
        """Construct a reward method class from the specified `config`.

        Args:
            metrics (list[:class:`.Metric`]): List of :class:`.Metric` objects to be used in this
                reward computation.
            config (:class:`.RewardConfig`): Configuration section defining the reward method to be used.

        Returns:
            (:class:`.Reward`): reward class to be used
        """
        return cls(metrics)

    def calculateMetrics(
        self,
        estimate_agent: EstimateAgent,
        sensor_agent: SensingAgent,
    ) -> ndarray:
        """Calculate each metric and saves to a dictionary.

        Args:
            estimate_agent (:class:`.EstimateAgent`): estimate agent for which this metric is being calculated
            sensor_agent (:class:`.SensorAgent`): sensor agent for which this metric is being calculated

        Returns:
            (``ndarray``): calculated metrics for the current simulation state
        """
        return array([metric.calculate(estimate_agent, sensor_agent) for metric in self.metrics])

    def normalizeMetrics(self, metric_matrix: ndarray) -> ndarray:
        """Normalize a given metric between 0 and 1 across the current predict.

        [TODO]: Add functionality for different normalization techniques.
        """
        for met in range(len(self.metrics)):
            if metric_matrix[..., met].max() > 0.0:
                metric_matrix[..., met] /= metric_matrix[..., met].max()

        return metric_matrix

    @abstractmethod
    def calculate(self, metric_matrix: ndarray) -> ndarray:
        """Abstract function for calculating rewards based on the simulation state.

        Note:
            Must be overridden by implementors.

        Args:
            metric_matrix (``ndarray``): 2D array of metrics

        Returns:
            ``ndarray``: calculated reward
        """
        raise NotImplementedError

    @property
    def metrics(self) -> list[Metric]:
        """``list``: metric objects used to calculate the reward."""
        return self._metrics
