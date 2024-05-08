from __future__ import annotations

# Standard Library Imports
from datetime import datetime
from unittest.mock import MagicMock, create_autospec

# Third Party Imports
import numpy as np
import pytest

# RESONAATE Imports
from resonaate.agents.estimate_agent import EstimateAgent
from resonaate.agents.sensing_agent import SensingAgent
from resonaate.physics.constants import DAYS2SEC
from resonaate.sensors.sensor_base import Sensor


@pytest.fixture(name="mocked_estimate")
def getMockedEstimateObject() -> EstimateAgent:
    """Create a mocked :class:`.EstimateAgent` object."""
    estimate = create_autospec(spec=EstimateAgent, instance=True)
    estimate.nominal_filter = create_autospec(spec=EstimateAgent, instance=True)
    estimate.nominal_filter.pred_x = np.array(
        [
            2.65384550e03,
            -4.89667126e02,
            6.75073870e03,
            -1.36159013e00,
            7.19231774e00,
            1.05193500e00,
        ],
    )
    estimate.nominal_filter.pred_p = np.array(
        [
            [2.0e-04, 0.0e00, 0.0e00, 0.0e00, 0.0e00, 0.0e00],
            [0.0e00, 2.0e-04, 0.0e00, 0.0e00, 0.0e00, 0.0e00],
            [0.0e00, 0.0e00, 2.0e-04, 0.0e00, 0.0e00, 0.0e00],
            [0.0e00, 0.0e00, 0.0e00, 2.0e-9, 0.0e00, 0.0e00],
            [0.0e00, 0.0e00, 0.0e00, 0.0e00, 2.0e-9, 0.0e00],
            [0.0e00, 0.0e00, 0.0e00, 0.0e00, 0.0e00, 2.0e-9],
        ],
    )
    estimate.nominal_filter.est_x = np.array(
        [
            2.93360025e03,
            -2.59149162e03,
            6.12785568e03,
            -4.88899365e-01,
            6.71106022e00,
            3.06846558e00,
        ],
    )
    estimate.nominal_filter.est_p = np.array(
        [
            [1.0e-04, 0.0e00, 0.0e00, 0.0e00, 0.0e00, 0.0e00],
            [0.0e00, 1.0e-04, 0.0e00, 0.0e00, 0.0e00, 0.0e00],
            [0.0e00, 0.0e00, 1.0e-04, 0.0e00, 0.0e00, 0.0e00],
            [0.0e00, 0.0e00, 0.0e00, 1.0e-9, 0.0e00, 0.0e00],
            [0.0e00, 0.0e00, 0.0e00, 0.0e00, 1.0e-9, 0.0e00],
            [0.0e00, 0.0e00, 0.0e00, 0.0e00, 0.0e00, 1.0e-9],
        ],
    )
    estimate.nominal_filter.cross_cvr = np.array(
        [
            [1.79296728e-10, 7.86887171e-12, -1.00801146e-06, -9.51272706e-10],
            [2.77791287e-10, -1.89021245e-10, 3.66385253e-07, 1.68460218e-09],
            [1.20658685e-10, 3.61926233e-10, 5.05902101e-07, 2.68658081e-09],
            [-3.99419639e-14, -1.33959325e-13, 2.35517983e-11, -2.96946975e-12],
            [-7.77013112e-14, -1.80179387e-14, -2.81226071e-10, 2.31623526e-13],
            [-6.60450355e-14, 1.61556233e-13, 4.33291706e-10, 1.79400632e-12],
        ],
    )
    estimate.nominal_filter.time = 60.0
    estimate.initial_covariance = estimate.nominal_filter.est_p
    estimate.last_observed_at = 2458454.0
    estimate.julian_date_epoch = 2458454.0 + 60.0 / DAYS2SEC
    estimate.eci_state = np.ones(6) * 2
    return estimate


@pytest.fixture(scope="class", name="mocked_sensor")
def getMockedSensorObject() -> Sensor:
    """Create a mocked :class:`.Sensor` object."""
    sensor = create_autospec(spec=Sensor, instance=True)
    sensor.r_matrix = np.array(
        [
            [7.22430673e-12, 0.00000000e00, 0.00000000e00, 0.00000000e00],
            [0.00000000e00, 6.58247782e-12, 0.00000000e00, 0.00000000e00],
            [0.00000000e00, 0.00000000e00, 9.00000000e-10, 0.00000000e00],
            [0.00000000e00, 0.00000000e00, 0.00000000e00, 1.00000000e-14],
        ],
    )
    sensor.deltaBoresight = MagicMock(return_value=4.0)
    sensor.slew_rate = 2.0
    return sensor


@pytest.fixture(scope="class", name="mocked_sensing_agent")
def getMockedSensingAgentObject(mocked_sensor: Sensor) -> SensingAgent:
    """Create a mocked :class:`.SensingAgent` object."""
    sensing_agent = create_autospec(spec=SensingAgent, instance=True)
    sensing_agent.sensors = mocked_sensor
    sensing_agent.eci_state = np.ones(6)
    sensing_agent.datetime_epoch = datetime(2018, 12, 1, 12)
    return sensing_agent
