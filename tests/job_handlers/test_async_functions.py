# pylint: disable=unused-argument
from __future__ import annotations

# Standard Library Imports
from typing import TYPE_CHECKING

# Third Party Imports
import pytest

# RESONAATE Imports
import resonaate.estimation.sequential.unscented_kalman_filter
import resonaate.job_handlers.task_prediction
from resonaate.job_handlers.task_prediction import asyncCalculateReward
from resonaate.tasking.metrics.metric_base import INFORMATION_METRIC_LABEL, Metric
from resonaate.tasking.rewards import SimpleSummationReward

# Type Checking Imports
if TYPE_CHECKING:
    # Standard Library Imports
    from collections.abc import Callable
    from typing import Any

    # RESONAATE Imports
    from resonaate.agents.agent_base import Agent
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
    info_metric.METRIC_TYPE = INFORMATION_METRIC_LABEL
    return [info_metric]


def testAsyncCalculateReward(
    monkeypatch: pytest.MonkeyPatch,
    estimate_agent: EstimateAgent,
    sensor_agent: SensingAgent,
    metric_list: list[Metric],
    mocked_kvs_get_func: Callable[[str], dict[int, Agent]],
    mocked_pickle_loads_func: Callable[[Any], object],
):
    """Test asyncCalculateReward().

    Args:
        monkeypatch (pytest.MonkeyPatch): Patch variable
        estimate_agent (EstimateAgent): Mock Estimate Agent
        sensor_agent (SensingAgent): Mock Sensor Agent
        metric_list (list[Metric]): list of metric objects
        mocked_kvs_get_func (Callable): mocked version of KVS.getValue() that returns agent dict
        mocked_pickle_loads_func (Callable): mocked version of pickle.loads() that bypasses any serialization
    """
    sensor_agent.simulation_id = 11111
    reward_class = SimpleSummationReward(metric_list)

    monkeypatch.setattr(
        resonaate.job_handlers.task_prediction.KeyValueStore, "getValue", mocked_kvs_get_func
    )
    monkeypatch.setattr(resonaate.job_handlers.task_prediction, "loads", mocked_pickle_loads_func)

    def mockForecast(*args, **kwargs):  # pylint:disable=unused-argument
        return None

    monkeypatch.setattr(
        resonaate.estimation.sequential.unscented_kalman_filter.UnscentedKalmanFilter,
        "forecast",
        mockForecast,
    )

    reward_dict = asyncCalculateReward(
        estimate_agent.simulation_id, reward_class, [sensor_agent.simulation_id]
    )
    assert reward_dict["visibility"][0]
