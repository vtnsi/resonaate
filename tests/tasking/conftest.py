from __future__ import annotations

# Standard Library Imports
from unittest.mock import create_autospec

# Third Party Imports
import numpy as np
import pytest

# RESONAATE Imports
from resonaate.agents.estimate_agent import EstimateAgent
from resonaate.agents.sensing_agent import SensingAgent
from resonaate.sensors.sensor_base import Sensor


@pytest.fixture(name="mocked_estimate")
def getMockedEstimateObject() -> EstimateAgent:
    """Create a mocked :class:`.EstimateAgent` object."""
    estimate = create_autospec(spec=SensingAgent, instance=True)
    estimate.nominal_filter = create_autospec(spec=SensingAgent, instance=True)
    estimate.nominal_filter.pred_p = np.array([[4, 23], [1, 67]])
    estimate.nominal_filter.est_p = np.array([[1, 1], [2, 4]])
    estimate.nominal_filter.cross_cvr = np.array([[3, 1, 12], [12, 344, 2]])
    estimate.nominal_filter.time = 60.0
    estimate.initial_covariance = np.array([[1, 1], [3, 2]])
    estimate.last_observed_at = 2458454.0
    estimate.julian_date_epoch = 2458454.0 + 60.0 / (24 * 60 * 60)
    return estimate


@pytest.fixture(scope="class", name="mocked_sensor")
def getMockedSensorObject() -> Sensor:
    """Create a mocked :class:`.Sensor` object."""
    sensor = create_autospec(spec=SensingAgent, instance=True)
    sensor.r_matrix = np.array([[7.0e-4, 0.0, 0.0], [0.0, 6.5e-4, 0.0], [0.0, 0.0, 8.0e-4]])
    sensor.delta_boresight = 4.0
    sensor.slew_rate = 2.0
    return sensor


@pytest.fixture(scope="class", name="mocked_sensing_agent")
def getMockedSensingAgentObject(mocked_sensor: Sensor) -> SensingAgent:
    """Create a mocked :class:`.SensingAgent` object."""
    sensing_agent = create_autospec(spec=SensingAgent, instance=True)
    mocked_sensor.r_matrix = np.array([[7.0e-4, 0.0, 0.0], [0.0, 6.5e-4, 0.0], [0.0, 0.0, 8.0e-4]])
    mocked_sensor.delta_boresight = 4.0
    mocked_sensor.slew_rate = 2.0

    sensing_agent.sensors = mocked_sensor
    return sensing_agent
