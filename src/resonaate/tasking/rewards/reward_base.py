"""Abstract :class:`.Reward` base class defining the reward API."""
# Standard Library Imports
from abc import ABCMeta, abstractmethod

# Local Imports
from ..metrics.metric_base import Metric


class Reward(metaclass=ABCMeta):
    """Abstract base class to encapsulate behavior of general reward methods."""

    REGISTRY = {}
    """Global reward object registry."""

    def __init__(self, metrics):
        """Construct a reward object with a set of metrics.

        Args:
            metrics (list): metrics to include in the reward calculation

        Raises:
            TypeError: raised if invalid :class:`.Metric` objects are passed
        """
        if isinstance(metrics, Metric):
            metrics = [metrics]
        if not all(isinstance(metric, Metric) for metric in metrics):
            raise TypeError("Reward constructor must be given Metric objects.")
        self._metrics = metrics

    @classmethod
    def register(cls, name, reward):
        """Register an implemented reward class in the global registry.

        Args:
            name (str): name to store as the key in the registry
            reward (:class:`.Reward`): reward object to register

        Raises:
            TypeError: raised if not providing a valid :class:`.Reward` sub-class
        """
        if not issubclass(reward, Reward):
            raise TypeError(type(reward))
        cls.REGISTRY[name] = reward

    @property
    def is_registered(self):
        """bool: return if an implemented reward class is registered."""
        return self.__class__.__name__ in self.REGISTRY

    def calculateMetrics(self, target_agents, target_id, sensor_agents, sensor_id, **kwargs):
        """Calculate each metric and saves to a dictionary.

        Args:
            target_agents (dict): current target agents set
            target_id (int): unique id of target corresponding to the metric
            sensor_agents (dict): current sensor agents set
            sensor_id (int): unique id of sensor corresponding to the metric

        Returns:
            dict: calculated metrics for the current simulation state
        """
        metric_solutions = {}
        for metric in self.metrics:
            metric_solutions[metric] = metric(
                target_agents, target_id, sensor_agents, sensor_id, **kwargs
            )

        return metric_solutions

    @abstractmethod
    def _calculateReward(self, target_agents, target_id, sensor_agents, sensor_id, **kwargs):
        """Abstract function for calculating rewards based on the simulation state.

        Note:
            Must be overridden by implementors.

        Args:
            target_agents (dict): current target agents set
            target_id (int): unique id of target corresponding to the metric
            sensor_agents (dict): current sensor agents set
            sensor_id (int): unique id of sensor corresponding to the metric

        Returns:
            ``numpy.ndarray``: calculated reward
        """
        raise NotImplementedError

    def __call__(self, target_agents, target_id, sensor_agents, sensor_id, **kwargs):
        """Call operator '()' for reward objects.

        Args:
            target_agents (dict): current target agents set
            target_id (int): unique id of target corresponding to the metric
            sensor_agents (dict): current sensor agents set
            sensor_id (int): unique id of sensor corresponding to the metric

        Returns:
            ``numpy.ndarray``: calculated reward
        """
        return self._calculateReward(target_agents, target_id, sensor_agents, sensor_id, **kwargs)

    @property
    def metrics(self):
        """list: metric objects used to calculate the reward."""
        return self._metrics
