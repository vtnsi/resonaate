"""Define implemented reward functions used to evaluate sensor task opportunities."""
# Standard Library Imports
# Third Party Imports
from numpy import sign
# RESONAATE Imports
from .reward_base import Reward


class CostConstrainedReward(Reward):
    """Cost-constrained reward function.

    This function constrains the reward from a information metric by the sign
    of the stability metric, and subtracting the sensor metric.

    References:
        :cite:t:`nastasi_2018_diss`, Section 5.3.3
    """

    def __init__(self, metrics, delta=0.85, **kwargs):
        """Construct a cost-constrained reward function.

        Note:
            This class requires one metric of each of the following types:
                - :class:`.Information`
                - :class:`.Stability`
                - :class:`.Sensor`

        Args:
            metrics (list): metrics instances for calculating the reward
            delta (float, optional): ratio of information reward to sensor reward.
                Defaults to 0.85.

        Raises:
            ValueError: raised if not supplied three metric objects
            TypeError: raised if not supplied one of each metric type from:
                [:class:`.Stability`, :class:`.Information`, :class:`.Sensor`]
        """
        super().__init__(metrics, **kwargs)
        self._delta = delta
        if len(metrics) != 3:
            raise ValueError("Incorrect number of metrics being passed")
        stability, information, sensor = False, False, False
        for metric in metrics:
            if metric.metric_type == "stability":
                stability = True
            if metric.metric_type == "information":
                information = True
            if metric.metric_type == "sensor":
                sensor = True

        if not all([stability, information, sensor]):
            raise TypeError("Incorrect assignment of metrics")

    def _calculateReward(self, target_agents, target_id, sensor_agents, sensor_id, **kwargs):
        """Calculate the cost-constrained reward.

        Note:
            This implements the following equation:
                r = delta * (sign(stab) + info) - (1 - delta) * sens

        Args:
            target_agents (dict): current target agents set
            target_id (int): unique id of target corresponding to the metric
            sensor_agents (dict): current sensor agents set
            sensor_id (int): unique id of sensor corresponding to the metric

        Returns:
            ``numpy.ndarray``: calculated reward
        """
        metrics = self.calculateMetrics(
            target_agents,
            target_id,
            sensor_agents,
            sensor_id,
            **kwargs
        )
        for metric, value in metrics.items():
            if metric.metric_type == "stability":
                stability = value
            if metric.metric_type == "information":
                information = value
            if metric.metric_type == "sensor":
                sensor = value

        return self._delta * (sign(stability) + information) - (1 - self._delta) * sensor


class SimpleSummationReward(Reward):
    """Simple summation reward function.

    This function takes any range of metrics, and sums them all together.
    """

    def _calculateReward(self, target_agents, target_id, sensor_agents, sensor_id, **kwargs):
        """Calculate the reward as the direct sum of each metric.

        References:
            :cite:t:`kadan_2021_scitech_parametric`

        Args:
            target_agents (dict): current target agents set
            target_id (int): unique id of target corresponding to the metric
            sensor_agents (dict): current sensor agents set
            sensor_id (int): unique id of sensor corresponding to the metric

        Returns:
            ``numpy.ndarray``: summed reward
        """
        return sum(
            self.calculateMetrics(
                target_agents,
                target_id,
                sensor_agents,
                sensor_id,
                **kwargs
            ).values()
        )


class CombinedReward(Reward):
    """Combined Cost-constrained and staleness reward function.

    This function constrains the reward from a information metric by the sign
    of the stability metric, and subtracting the sensor metric.
    """

    def __init__(self, metrics, delta=0.85, **kwargs):
        """Construct a cost-constrained reward function.

        Note:
            This class requires one metric of each of the following types:
                - :class:`.Information`
                - :class:`.Stability`
                - :class:`.Sensor`
                - :class:`.Behavior`

        Args:
            metrics (list): metrics instances for calculating the reward
            delta (float, optional): ratio of information reward to sensor reward.
                Defaults to 0.85.

        Raises:
            ValueError: raised if not supplied three metric objects
            TypeError: raised if not supplied one of each metric type from:
                [:class:`.Stability`, :class:`.Information`, :class:`.Sensor`, :class:`.Behavior`]
        """
        super().__init__(metrics, **kwargs)
        self._delta = delta
        if len(metrics) != 4:
            raise ValueError("Incorrect number of metrics being passed")
        stability, information, sensor, behavior = False, False, False, False
        for metric in metrics:
            if metric.metric_type == "stability":
                stability = True
            if metric.metric_type == "information":
                information = True
            if metric.metric_type == "sensor":
                sensor = True
            if metric.metric_type == "behavior":
                behavior = True

        if not all([stability, information, sensor, behavior]):
            raise TypeError("Incorrect assignment of metrics")

    def _calculateReward(self, target_agents, target_id, sensor_agents, sensor_id, **kwargs):
        """Calculate the Combined cost-constrained staleness reward.

        References:
            :cite:t:`kadan_2021_scitech_parametric`

        Note:
            This implements the following equation:
                r = delta * (sign(stab) + info) - (1 - delta) * sens + staleness

        Args:
            target_agents (dict): current target agents set
            target_id (int): unique id of target corresponding to the metric
            sensor_agents (dict): current sensor agents set
            sensor_id (int): unique id of sensor corresponding to the metric

        Returns:
            ``numpy.ndarray``: calculated reward
        """
        metrics = self.calculateMetrics(
            target_agents,
            target_id,
            sensor_agents,
            sensor_id,
            **kwargs
        )
        for metric, value in metrics.items():
            if metric.metric_type == "stability":
                stability = value
            if metric.metric_type == "information":
                information = value
            if metric.metric_type == "sensor":
                sensor = value
            if metric.metric_type == "behavior":
                behavior = value

        return (self._delta * (sign(stability) + information) - (1 - self._delta) * sensor) + behavior
