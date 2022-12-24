# pylint: disable=unused-argument
from __future__ import annotations

# Standard Library Imports
from datetime import datetime
from typing import TYPE_CHECKING
from unittest.mock import create_autospec

# Third Party Imports
import numpy as np
import pytest

# RESONAATE Imports
from resonaate.agents.estimate_agent import EstimateAgent
from resonaate.agents.sensing_agent import SensingAgent
from resonaate.agents.target_agent import TargetAgent
from resonaate.dynamics.two_body import TwoBody
from resonaate.estimation.maneuver_detection import StandardNis
from resonaate.estimation.sequential.unscented_kalman_filter import UnscentedKalmanFilter
from resonaate.scenario.clock import ScenarioClock
from resonaate.scenario.config.estimation_config import InitialOrbitDeterminationConfig
from resonaate.sensors.sensor_base import Sensor

# Type Checking Imports
if TYPE_CHECKING:
    # Standard Library Imports
    from collections.abc import Callable
    from typing import Any

    # RESONAATE Imports
    from resonaate.agents.agent_base import Agent


@pytest.fixture(scope="class", name="mocked_sensor")
def getMockedSensorObject() -> Sensor:
    """Create a mocked :class:`.Sensor` object."""
    sensor = create_autospec(Sensor, instance=True)
    sensor.r_matrix = np.array([[7.0e-4, 0.0, 0.0], [0.0, 6.5e-4, 0.0], [0.0, 0.0, 8.0e-4]])
    sensor.delta_boresight = 4.0
    sensor.slew_rate = 2.0
    return sensor


@pytest.fixture(scope="class", name="sensor_agent")
def getMockedSensingAgentObject(mocked_sensor: Sensor) -> SensingAgent:
    """Create a mocked :class:`.SensingAgent` object."""
    sensing_agent = create_autospec(SensingAgent, instance=True)
    sensing_agent.sensors = mocked_sensor
    sensing_agent.simulation_id = 11111
    return sensing_agent


@pytest.fixture(name="scenario_clock")
def createScenarioClock(reset_shared_db: None) -> ScenarioClock:
    """Create a :class:`.ScenarioClock` object for use in testing."""
    return ScenarioClock(datetime(2018, 12, 1, 12, 0), 300, 60)


@pytest.fixture(name="target_agent")
def createTargetAgent(scenario_clock: ScenarioClock) -> TargetAgent:
    """Create valid target agent for testing propagate jobs."""
    agent = TargetAgent(
        11111,
        "test_tgt",
        "Spacecraft",
        np.asarray([6378.0, 2.0, 10.0, 0.0, 0.0, 0.0]),
        scenario_clock,
        TwoBody(),
        True,
        25.0,
        500.0,
        0.21,
    )
    return agent


@pytest.fixture(name="estimate_agent")
def createEstimateAgent(target_agent: TargetAgent, scenario_clock: ScenarioClock) -> EstimateAgent:
    """Create valid estimate agent for testing propagate jobs."""
    est_x = np.asarray([6378.0, 2.0, 10.0, 0.0, 0.0, 0.0])
    est_p = np.diagflat([1.0, 2.0, 1.0, 0.001, 0.002, 0.001])
    agent = EstimateAgent(
        target_agent.simulation_id,
        target_agent.name,
        target_agent.agent_type,
        scenario_clock,
        est_x,
        est_p,
        UnscentedKalmanFilter(
            target_agent.simulation_id,
            scenario_clock.time,
            est_x,
            est_p,
            TwoBody(),
            3 * est_p,
            StandardNis(0.01),
            None,
            False,
        ),
        None,
        InitialOrbitDeterminationConfig(),
        25.0,
        500.0,
        0.21,
    )
    return agent


@pytest.fixture(name="mocked_kvs_get_func")
def mockKVSGetValue(
    sensor_agent: SensingAgent,
    estimate_agent: EstimateAgent,
    target_agent: TargetAgent,
) -> Callable[[str], dict[int, Agent]]:
    """Provides a mocked version of the KVS.getValue() function."""

    def kvsGet(key: str) -> dict[int, Agent]:
        """Mock that returns proper dict based on input arguments."""
        if key == "sensor_agents":
            return {sensor_agent.simulation_id: sensor_agent}

        if key == "estimate_agents":
            return {estimate_agent.simulation_id: estimate_agent}

        if key == "target_agents":
            return {target_agent.simulation_id: target_agent}

        raise ValueError("Bad argument to mocked KVS.getValue() func")

    return kvsGet


@pytest.fixture(name="mocked_pickle_loads_func")
def mockPickleLoads() -> Callable[[Any], object]:
    """Provides a mocked version of the pickle.loads() function that just passes through data."""

    def pickleLoad(data: Any) -> object:
        """Simple mock for skipping pickling of data."""
        return data

    return pickleLoad
