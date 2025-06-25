from __future__ import annotations

# Standard Library Imports
from typing import TYPE_CHECKING

# Third Party Imports
import numpy as np
import pytest

# RESONAATE Imports
from resonaate.common.labels import MetricTypeLabel
from resonaate.tasking.metrics.metric_base import Metric
from resonaate.tasking.rewards.reward_base import Reward
from resonaate.tasking.rewards.rewards import (
    CombinedReward,
    CostConstrainedReward,
    SimpleSummationReward,
)

# Type Checking Imports
if TYPE_CHECKING:
    # Third Party Imports
    from numpy import ndarray

    # RESONAATE Imports
    from resonaate.agents.estimate_agent import EstimateAgent
    from resonaate.agents.sensing_agent import SensingAgent


@pytest.fixture(name="stub_reward_class")
def stubRewardClass() -> Reward:
    """Return reference to a minimal :class:`.Reward` class."""

    class StubReward(Reward):
        def calculate(self, metric_matrix: ndarray):
            return 3

    return StubReward


@pytest.fixture(name="stub_metric_class")
def stubMetricClass() -> Metric:
    """Return reference to a minimal :class:`.Metric` class."""

    class StubMetric(Metric):
        def calculate(self, estimate_agent: EstimateAgent, sensor_agent: SensingAgent):
            return 3

    return StubMetric


class TestRewardBase:
    """Test the base class of the reward module."""

    def testCreation(self, stub_metric_class: Metric):
        """Test creating a Decision Object.

        Args:
            stub_metric_class (:class:`.Metric`): Mock Metric
        """
        with pytest.raises(TypeError):
            Reward(stub_metric_class())

    def testBadMetricType(self):
        """Test when a non-metric is passed into the `Reward` Init."""
        non_iterable = "string"
        with pytest.raises(TypeError):
            Reward(non_iterable)

        bad_list = [non_iterable]
        with pytest.raises(TypeError):
            Reward(bad_list)

    def testNormalizeMetrics(self, stub_reward_class: Reward, stub_metric_class: Metric):
        """Test normalizeMetrics().

        Args:
            stub_reward_class (:class:`.Reward`): Mock Reward
            stub_metric_class (:class:`.Metric`): Mock Metric
        """
        test_reward = stub_reward_class(stub_metric_class())
        metric_matrix = np.array([[[0.1]], [[2.0]], [[3.0]]])
        metrics = test_reward.normalizeMetrics(metric_matrix)
        assert metrics.max() <= 1.0


class TestCostConstrainedReward:
    """Test the CostConstrainedReward class of the reward module."""

    @pytest.fixture(name="metric_list")
    def getMetricList(self, stub_metric_class: Metric):
        """Create list of metrics to assign proper metric length of Reward Function calls.

        Args:
            stub_metric_class (:class:`.Metric`): Mock Metric

        Returns:
            list: :class:`.Metric` objects
        """
        info_metric = stub_metric_class()
        info_metric.METRIC_TYPE = MetricTypeLabel.INFORMATION
        stability_metric = stub_metric_class()
        stability_metric.METRIC_TYPE = MetricTypeLabel.STABILITY
        sensor_metric = stub_metric_class()
        sensor_metric.METRIC_TYPE = MetricTypeLabel.SENSOR
        return [info_metric, stability_metric, sensor_metric]

    def testBadMetricType(self, metric_list: list[Metric], stub_metric_class: Metric):
        """Test bad entries into `CostConstrainedReward`.

        Args:
            metric_list (``list``): :class:`.Metric` objects
            stub_metric_class (:class:`.Metric`): Mock Metric
        """
        behavior_metric = stub_metric_class()
        behavior_metric.METRIC_TYPE = MetricTypeLabel.TARGET
        metric_list.append(behavior_metric)
        with pytest.raises(ValueError, match="Incorrect number of metrics being passed"):
            CostConstrainedReward(metric_list)

        metric_list.pop(0)
        with pytest.raises(TypeError):
            _ = CostConstrainedReward(metric_list)

    def testCalculateReward(
        self,
        metric_list: list[Metric],
    ):
        """Test _calculateReward() function of the CostConstrainedReward class."""
        reward = CostConstrainedReward(metric_list)
        metrics = np.ones(len(metric_list))
        reward.calculate(metrics)


class TestSimpleSummationReward:
    """Test the SimpleSummationReward class of the reward module."""

    @pytest.fixture(name="metric_list")
    def getMetricList(self, stub_metric_class: Metric):
        """Create list of metrics to assign proper metric length of Reward Function calls.

        Args:
            stub_metric_class (:class:`.Metric`): Mock Metric

        Returns:
            list: :class:`.Metric` objects
        """
        info_metric = stub_metric_class()
        info_metric.METRIC_TYPE = MetricTypeLabel.INFORMATION
        return [info_metric]

    def testCalculateReward(
        self,
        metric_list: list[Metric],
    ):
        """Test _calculateReward() function of the SimpleSummationReward class."""
        reward = SimpleSummationReward(metric_list)
        metrics = np.array([[[1.0]], [[2.0]]])
        reward.calculate(metrics)


class TestCombinedReward:
    """Test the CombinedReward class of the reward module."""

    @pytest.fixture(name="metric_list")
    def getMetricList(self, stub_metric_class: Metric):
        """Create list of metrics to assign proper metric length of Reward Function calls."""
        info_metric = stub_metric_class()
        info_metric.METRIC_TYPE = MetricTypeLabel.INFORMATION
        stability_metric = stub_metric_class()
        stability_metric.METRIC_TYPE = MetricTypeLabel.STABILITY
        sensor_metric = stub_metric_class()
        sensor_metric.METRIC_TYPE = MetricTypeLabel.SENSOR
        behavior_metric = stub_metric_class()
        behavior_metric.METRIC_TYPE = MetricTypeLabel.TARGET
        return [info_metric, stability_metric, sensor_metric, behavior_metric]

    def testBadMetricType(self, metric_list: list[Metric], stub_metric_class: Metric):
        """Test bad entries into `CostConstrainedReward`.

        Args:
            metric_list (``list``): :class:`.Metric` objects
            stub_metric_class (:class:`.Metric`): Mock Metric
        """
        behavior_metric = stub_metric_class()
        behavior_metric.METRIC_TYPE = MetricTypeLabel.TARGET
        metric_list.append(behavior_metric)
        with pytest.raises(ValueError, match="Incorrect number of metrics being passed"):
            _ = CombinedReward(metric_list)

        metric_list.pop(0)
        with pytest.raises(TypeError):
            _ = CombinedReward(metric_list)

    def testCalculateReward(
        self,
        metric_list: list[Metric],
    ):
        """Test _calculateReward() function of the CombinedReward class."""
        reward = CombinedReward(metric_list)
        metrics = np.ones(len(metric_list))
        reward.calculate(metrics)
