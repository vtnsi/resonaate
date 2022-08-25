from __future__ import annotations

# Standard Library Imports
from typing import TYPE_CHECKING

# Third Party Imports
import pytest

# RESONAATE Imports
from resonaate.tasking.metrics.metric_base import Metric
from resonaate.tasking.rewards.reward_base import Reward
from resonaate.tasking.rewards.rewards import (
    CombinedReward,
    CostConstrainedReward,
    SimpleSummationReward,
)

# Type Checking Imports
if TYPE_CHECKING:
    # RESONAATE Imports
    from resonaate.agents.estimate_agent import EstimateAgent
    from resonaate.agents.sensing_agent import SensingAgent


@pytest.fixture(name="stub_reward_class")
def stubRewardClass() -> Reward:
    """Return reference to a minimal :class:`.Reward` class."""

    class StubReward(Reward):
        def _calculateReward(self, estimate_agent, sensor_agent, **kwargs):
            return 3

    return StubReward


@pytest.fixture(name="stub_metric_class")
def stubMetricClass() -> Metric:
    """Return reference to a minimal :class:`.Metric` class."""

    class StubMetric(Metric):
        def _calculateMetric(self, estimate_agent, sensor_agent, **kwargs):
            return 3

    return StubMetric


class TestRewardBase:
    """Test the base class of the reward module."""

    def testRegistry(self, stub_reward_class: Reward, stub_metric_class: Metric):
        """Test to make sure the reward object is registered."""
        test_reward = stub_reward_class(stub_metric_class())
        assert test_reward.is_registered is False

        # Register new class and check
        Reward.register(stub_reward_class)
        test_reward = stub_reward_class(stub_metric_class())
        assert test_reward.is_registered is True

        # Ensure we cannot register objects that are not :class:`.Reward` sub-classes
        with pytest.raises(TypeError):
            Reward.register([True, False])

        with pytest.raises(TypeError):
            Reward.register(stub_metric_class)

    def testCreation(self, stub_metric_class: Metric):
        """Test creating a Decision Object."""
        with pytest.raises(TypeError):
            Reward(stub_metric_class())  # pylint: disable=abstract-class-instantiated

    def testCalculateReward(
        self,
        stub_reward_class: Reward,
        stub_metric_class: Metric,
        mocked_estimate: EstimateAgent,
        mocked_sensor: SensingAgent,
    ):
        """Test the call function of the Reward base class."""
        target_agents = {11111: mocked_estimate}
        target_id = 11111
        sensor_agents = {"sensor": mocked_sensor}
        sensor_id = "sensor"
        reward = stub_reward_class(stub_metric_class())
        reward(target_agents[target_id], sensor_agents[sensor_id])


class TestCostConstrainedReward:
    """Test the CostConstrainedReward class of the reward module."""

    @pytest.fixture(name="metric_list")
    def getMetricList(self, stub_metric_class: Metric):
        """Create list of metrics to assign proper metric length of Reward Function calls."""
        info_metric = stub_metric_class()
        info_metric.METRIC_TYPE = "information"
        stability_metric = stub_metric_class()
        stability_metric.METRIC_TYPE = "stability"
        sensor_metric = stub_metric_class()
        sensor_metric.METRIC_TYPE = "sensor"
        return [info_metric, stability_metric, sensor_metric]

    def testRegistry(self, metric_list: list[Metric]):
        """Test to make sure the reward object is registered."""
        reward = CostConstrainedReward(metric_list)
        assert reward.is_registered is True

    def testRewardCall(
        self,
        metric_list: list[Metric],
        mocked_estimate: EstimateAgent,
        mocked_sensor: SensingAgent,
    ):
        """Test the call function of the CostConstrainedReward class."""
        target_agents = {11111: mocked_estimate}
        target_id = 11111
        sensor_agents = {"sensor": mocked_sensor}
        sensor_id = "sensor"
        reward = CostConstrainedReward(metric_list)
        reward(target_agents[target_id], sensor_agents[sensor_id])


class TestSimpleSummationReward:
    """Test the SimpleSummationReward class of the reward module."""

    @pytest.fixture(name="metric_list")
    def getMetricList(self, stub_metric_class: Metric):
        """Create list of metrics to assign proper metric length of Reward Function calls."""
        info_metric = stub_metric_class()
        info_metric.METRIC_TYPE = "information"
        stability_metric = stub_metric_class()
        stability_metric.METRIC_TYPE = "stability"
        sensor_metric = stub_metric_class()
        sensor_metric.METRIC_TYPE = "sensor"
        behavior_metric = stub_metric_class()
        behavior_metric.METRIC_TYPE = "behavior"
        return [info_metric, stability_metric, sensor_metric, behavior_metric]

    def testRegistry(self, metric_list: list[Metric]):
        """Test to make sure the reward object is registered."""
        reward = SimpleSummationReward(metric_list)
        assert reward.is_registered is True

    def testRewardCall(
        self,
        metric_list: list[Metric],
        mocked_estimate: EstimateAgent,
        mocked_sensor: SensingAgent,
    ):
        """Test the call function of the SimpleSummationReward class."""
        target_agents = {11111: mocked_estimate}
        target_id = 11111
        sensor_agents = {"sensor": mocked_sensor}
        sensor_id = "sensor"
        reward = SimpleSummationReward(metric_list)
        reward(target_agents[target_id], sensor_agents[sensor_id])


class TestCombinedReward:
    """Test the CombinedReward class of the reward module."""

    @pytest.fixture(name="metric_list")
    def getMetricList(self, stub_metric_class: Metric):
        """Create list of metrics to assign proper metric length of Reward Function calls."""
        info_metric = stub_metric_class()
        info_metric.METRIC_TYPE = "information"
        stability_metric = stub_metric_class()
        stability_metric.METRIC_TYPE = "stability"
        sensor_metric = stub_metric_class()
        sensor_metric.METRIC_TYPE = "sensor"
        behavior_metric = stub_metric_class()
        behavior_metric.METRIC_TYPE = "behavior"
        return [info_metric, stability_metric, sensor_metric, behavior_metric]

    def testRegistry(self, metric_list: list[Metric]):
        """Test to make sure the reward object is registered."""
        reward = CombinedReward(metric_list)
        assert reward.is_registered is True

    def testRewardCall(
        self,
        metric_list: list[Metric],
        mocked_estimate: EstimateAgent,
        mocked_sensor: SensingAgent,
    ):
        """Test the call function of the CombinedReward class."""
        target_agents = {11111: mocked_estimate}
        target_id = 11111
        sensor_agents = {"sensor": mocked_sensor}
        sensor_id = "sensor"
        reward = CombinedReward(metric_list)
        reward(target_agents[target_id], sensor_agents[sensor_id])
