# pylint: disable=attribute-defined-outside-init
# Standard Library Imports
# Third Party Imports
import pytest

try:
    # RESONAATE Imports
    from resonaate.tasking.metrics.metric_base import Metric
    from resonaate.tasking.rewards.reward_base import Reward
    from resonaate.tasking.rewards.rewards import CostConstrainedReward, SimpleSummationReward
except ImportError as error:
    raise Exception(f"Please ensure you have appropriate packages installed:\n {error}") from error
# Local Imports
# Testing Imports
from ..conftest import BaseTestCase


@pytest.fixture(name="mocked_reward_class")
def mockedRewardClass():
    """Return reference to a minimal :class:`.Reward` class."""

    class MockedReward(Reward):
        def _calculateReward(self, estimate_agent, sensor_agent, **kwargs):
            return 3

    return MockedReward


@pytest.fixture(name="mocked_metric_class")
def mockedMetricClass():
    """Return reference to a minimal :class:`.Metric` class."""

    class MockedMetric(Metric):
        def _calculateMetric(self, estimate_agent, sensor_agent, **kwargs):
            return 3

    return MockedMetric


class TestRewardBase(BaseTestCase):
    """Test the base class of the reward module."""

    def testRegistry(self, mocked_reward_class, mocked_metric):
        """Test to make sure the reward object is registered."""
        test_reward = mocked_reward_class(mocked_metric)
        assert test_reward.is_registered is False

        # Register new class and check
        Reward.register("MockedReward", mocked_reward_class)
        test_reward = mocked_reward_class(mocked_metric)
        assert test_reward.is_registered is True

        # Ensure we cannot register objects that are not :class:`.Reward` sub-classes
        with pytest.raises(TypeError):
            Reward.register("MockedReward", [True, False])

    def testCreation(self, mocked_metric):
        """Test creating a Decision Object."""
        with pytest.raises(TypeError):
            Reward(mocked_metric)  # pylint: disable=abstract-class-instantiated

    def testCalculateReward(
        self, mocked_reward_class, mocked_metric, mocked_estimate, mocked_sensor
    ):
        """Test the call function of the Reward base class."""
        target_agents = {11111: mocked_estimate}
        target_id = 11111
        sensor_agents = {"sensor": mocked_sensor}
        sensor_id = "sensor"
        reward = mocked_reward_class(mocked_metric)
        reward(target_agents[target_id], sensor_agents[sensor_id])


class TestCostConstrainedReward(BaseTestCase):
    """Test the CostConstrainedReward class of the reward module."""

    @pytest.fixture(name="metric_list")
    def getMetricList(self, mocked_metric_class):
        """Create list of metrics to assign proper metric length of Reward Function calls."""
        info_metric = mocked_metric_class()
        info_metric.METRIC_TYPE = "information"
        stability_metric = mocked_metric_class()
        stability_metric.METRIC_TYPE = "stability"
        sensor_metric = mocked_metric_class()
        sensor_metric.METRIC_TYPE = "sensor"
        return [info_metric, stability_metric, sensor_metric]

    def testRegistry(self, metric_list):
        """Test to make sure the reward object is registered."""
        reward = CostConstrainedReward(metric_list)
        assert reward.is_registered is True

    def testRewardCall(self, metric_list, mocked_estimate, mocked_sensor):
        """Test the call function of the CostConstrainedReward class."""
        target_agents = {11111: mocked_estimate}
        target_id = 11111
        sensor_agents = {"sensor": mocked_sensor}
        sensor_id = "sensor"
        reward = CostConstrainedReward(metric_list)
        reward(target_agents[target_id], sensor_agents[sensor_id])


class TestSimpleSummationReward(BaseTestCase):
    """Test the SimpleSummationReward class of the reward module."""

    @pytest.fixture(name="metric_list")
    def getMetricList(self, mocked_metric_class):
        """Create list of metrics to assign proper metric length of Reward Function calls."""
        info_metric = mocked_metric_class()
        info_metric.METRIC_TYPE = "information"
        stability_metric = mocked_metric_class()
        stability_metric.METRIC_TYPE = "stability"
        sensor_metric = mocked_metric_class()
        sensor_metric.METRIC_TYPE = "sensor"
        behavior_metric = mocked_metric_class()
        behavior_metric.METRIC_TYPE = "behavior"
        return [info_metric, stability_metric, sensor_metric, behavior_metric]

    def testRegistry(self, metric_list):
        """Test to make sure the reward object is registered."""
        reward = SimpleSummationReward(metric_list)
        assert reward.is_registered is True

    def testRewardCall(self, metric_list, mocked_estimate, mocked_sensor):
        """Test the call function of the SimpleSummationReward class."""
        target_agents = {11111: mocked_estimate}
        target_id = 11111
        sensor_agents = {"sensor": mocked_sensor}
        sensor_id = "sensor"
        reward = SimpleSummationReward(metric_list)
        reward(target_agents[target_id], sensor_agents[sensor_id])
