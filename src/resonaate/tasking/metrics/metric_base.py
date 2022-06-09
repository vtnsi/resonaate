"""Abstract :class:`.Metric` base class defining the metric API."""
# Standard Library Imports
from abc import ABCMeta, abstractmethod
# Third Party Imports
# RESONAATE Imports


class Metric(metaclass=ABCMeta):
    """Abstract base class to encapsulate behavior of general metrics."""

    METRIC_TYPE = "base"
    """Type of metric in str format, for reward logic."""

    REGISTRY = {}
    """Global metric object registry."""

    @classmethod
    def register(cls, name, metric):
        """Register an implemented metric class in the global registry.

        Args:
            name (str): name to store as the key in the registry
            metric (:class:`.Metric`): metric object to register

        Raises:
            TypeError: raised if not providing a valid :class:`.Metric` sub-class
        """
        if not issubclass(metric, Metric):
            raise TypeError(type(metric))

        cls.REGISTRY[name] = metric

    @property
    def is_registered(self):
        """bool: return if an implemented metric class is registered."""
        return self.__class__.__name__ in self.REGISTRY

    @abstractmethod
    def _calculateMetric(self, target_agents, target_id, sensor_agents, sensor_id, **kwargs):
        """Abstract function for calculating the metric based on the set of targets & sensors.

        Note:
            Must be overridden by implementors.

        Args:
            target_agents (dict): current target agents set
            target_id (int): unique id of target corresponding to the metric
            sensor_agents (dict): current sensor agents set
            sensor_id (int): unique id of sensor corresponding to the metric

        Returns:
            float: single, target-sensor paired metric value
        """
        raise NotImplementedError

    def __call__(self, target_agents, target_id, sensor_agents, sensor_id, **kwargs):
        """Call operator '()' for metric objects.

        Args:
            target_agents (dict): current target agents set
            target_id (int): unique id of target corresponding to the metric
            sensor_agents (dict): current sensor agents set
            sensor_id (int): unique id of sensor corresponding to the metric

        Returns:
            float: single, target-sensor paired metric value
        """
        return self._calculateMetric(target_agents, target_id, sensor_agents, sensor_id, **kwargs)

    @property
    def metric_type(self):
        """str: return the type of metric in str format, for convenience."""
        return self.METRIC_TYPE


class InformationMetric(Metric):
    """Information metric type base class.

    These metrics should quantify the information (or uncertainty reduction) from
    predicted observations/estimates. These prioritize pure estimation performance.
    """

    METRIC_TYPE = "information"

    @abstractmethod
    def _calculateMetric(self, target_agents, target_id, sensor_agents, sensor_id, **kwargs):
        """Define logic for calculating metrics based on the given target/sensor sets.

        Must be overridden by implementors.
        """
        raise NotImplementedError


class StabilityMetric(Metric):
    """Stability metric type base class.

    These metrics quantify the stability of an estimate, and limit observations for
    well-estimated/observed targets.
    """

    METRIC_TYPE = "stability"

    @abstractmethod
    def _calculateMetric(self, target_agents, target_id, sensor_agents, sensor_id, **kwargs):
        """Define logic for calculating metrics based on the given target/sensor sets.

        Must be overridden by implementors.
        """
        raise NotImplementedError


class SensorMetric(Metric):
    """Sensor metric type base class.

    These metrics quantify the impact of observations on the actual sensor agent, and
    limit "costly" collections.
    """

    METRIC_TYPE = "sensor"

    @abstractmethod
    def _calculateMetric(self, target_agents, target_id, sensor_agents, sensor_id, **kwargs):
        """Define logic for calculating metrics based on the given target/sensor sets.

        Must be overridden by implementors.
        """
        raise NotImplementedError


class BehaviorMetric(Metric):
    """Behavior metric type base class.

    These metrics are ad-hoc behaviors that do not fit into another metric type. These
    prioritize specific behaviors of the sensors/estimates.
    """

    METRIC_TYPE = "behavior"

    @abstractmethod
    def _calculateMetric(self, target_agents, target_id, sensor_agents, sensor_id, **kwargs):
        """Define logic for calculating metrics based on the given target/sensor sets.

        Must be overridden by implementors.
        """
        raise NotImplementedError
