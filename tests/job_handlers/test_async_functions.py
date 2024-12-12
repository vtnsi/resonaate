from __future__ import annotations

# Standard Library Imports
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, create_autospec, patch

# Third Party Imports
import numpy as np
import pytest

# RESONAATE Imports
from resonaate.common.labels import MetricTypeLabel
from resonaate.data.observation import Observation
from resonaate.job_handlers.task_prediction import asyncCalculateReward
from resonaate.tasking.metrics.metric_base import Metric
from resonaate.tasking.rewards import SimpleSummationReward

# Type Checking Imports
if TYPE_CHECKING:
    # Standard Library Imports

    # RESONAATE Imports
    from resonaate.agents.estimate_agent import EstimateAgent
    from resonaate.agents.sensing_agent import SensingAgent


@pytest.fixture(name="stub_metric_class")
def stubMetricClass() -> Metric:
    """Return reference to a minimal :class:`.Metric` class."""

    class StubMetric(Metric):
        def calculate(self, estimate_agent: EstimateAgent, sensor_agent: SensingAgent, **kwargs):
            return 3

    return StubMetric


@pytest.fixture(name="metric_list")
def getMetricList(stub_metric_class: Metric):
    """Create list of metrics to assign proper metric length of Reward Function calls."""
    info_metric = stub_metric_class()
    info_metric.METRIC_TYPE = MetricTypeLabel.INFORMATION
    return [info_metric]


def testAsyncCalculateReward(
    estimate_agent: EstimateAgent,
    sensor_agent: SensingAgent,
    metric_list: list[Metric],
):
    """Test asyncCalculateReward().

    Args:
        estimate_agent (EstimateAgent): Mock Estimate Agent
        sensor_agent (SensingAgent): Mock Sensor Agent
        metric_list (list[Metric]): list of metric objects
    """
    sensor_agent.simulation_id = 11111
    reward_class = SimpleSummationReward(metric_list)

    patcher = patch("resonaate.job_handlers.task_prediction.AgentCaches", autospec=True)
    mocked_agent_caches = patcher.start()
    mocked_agent_caches.sensors.getAgent = MagicMock()
    mocked_agent_caches.sensors.getAgent.return_value = sensor_agent
    mocked_agent_caches.estimates.getAgent = MagicMock()
    mocked_agent_caches.estimates.getAgent.return_value = estimate_agent

    base_reward = 10.0
    # Predicted Observation
    reward_class.calculateMetrics = MagicMock(return_value=base_reward)
    estimate_agent.nominal_filter.forecast = MagicMock()

    with patch(
        "resonaate.job_handlers.task_prediction.predictObservation",
        return_value=create_autospec(Observation, instance=True),
    ) as mock_predict_obs:
        reward_dict = asyncCalculateReward(
            estimate_agent.simulation_id,
            reward_class,
            [sensor_agent.simulation_id],
        )
        mock_predict_obs.assert_called_once()
        estimate_agent.nominal_filter.forecast.assert_called_once()
        reward_class.calculateMetrics.assert_called_once()
        assert reward_dict["estimate_id"] == estimate_agent.simulation_id
        assert reward_dict["visibility"][0]
        assert (
            reward_dict["metric_matrix"]
            == np.ones_like(reward_dict["metric_matrix"]) * base_reward
        )

    # No Predicted Observation
    reward_class.calculateMetrics.reset_mock()
    estimate_agent.nominal_filter.forecast.reset_mock()

    with patch(
        "resonaate.job_handlers.task_prediction.predictObservation",
        return_value=None,
    ) as mock_predict_obs:
        reward_dict = asyncCalculateReward(
            estimate_agent.simulation_id,
            reward_class,
            [sensor_agent.simulation_id],
        )
        mock_predict_obs.assert_called_once()
        estimate_agent.nominal_filter.forecast.assert_not_called()
        reward_class.calculateMetrics.assert_not_called()
        assert reward_dict["estimate_id"] == estimate_agent.simulation_id
        assert not reward_dict["visibility"][0]
        assert reward_dict["metric_matrix"] == np.zeros_like(reward_dict["metric_matrix"])
