from __future__ import annotations

# Standard Library Imports
from copy import deepcopy
from datetime import datetime
from unittest.mock import MagicMock, create_autospec

# Third Party Imports
import pytest
from numpy import array, zeros

# RESONAATE Imports
from resonaate.agents.estimate_agent import EstimateAgent
from resonaate.agents.sensing_agent import SensingAgent
from resonaate.dynamics.two_body import TwoBody
from resonaate.estimation.kalman.unscented_kalman_filter import UnscentedKalmanFilter
from resonaate.estimation.maneuver_detection import StandardNis
from resonaate.physics.time.stardate import ScenarioTime
from resonaate.physics.transforms.methods import getSlantRangeVector
from resonaate.scenario.clock import ScenarioClock
from resonaate.scenario.config.agent_config import SensingAgentConfig
from resonaate.scenario.config.estimation_config import InitialOrbitDeterminationConfig

SENSOR_CONFIG = {
    "name": "Test Radar",
    "id": 200000,
    "platform": {"type": "ground_facility"},
    "state": {
        "type": "lla",
        "latitude": 0.2281347875532986,
        "longitude": 0.5432822498364406,
        "altitude": 0.095,
    },
    "sensor": {
        "covariance": [
            [3.0461741978670863e-12, 0.0, 0.0, 0.0],
            [0.0, 3.0461741978670863e-12, 0.0, 0.0],
            [0.0, 0.0, 2.5000000000000004e-11, 0.0],
            [0.0, 0.0, 0.0, 4.0000000000000015e-12],
        ],
        "slew_rate": 5.0,
        "azimuth_range": [0.0, 359.9999],
        "elevation_range": [5.0, 89.9999],
        "efficiency": 0.95,
        "aperture_diameter": 26.0,
        "type": "radar",
        "background_observations": True,
        "tx_power": 2.5e6,
        "tx_frequency": 1.5e9,
        "min_detectable_power": 1.4314085925969573e-14,
    },
}


@pytest.fixture(name="clock")
def getScenarioClock(database: None) -> ScenarioClock:
    """Get a ScenarioClock."""
    start_date = datetime(2020, 6, 6, 0, 0)
    return ScenarioClock(start_date, 60.0, 30.0)


@pytest.fixture(name="conic_sensor_agent")
def getConicFOVSensingAgent(clock: ScenarioClock) -> SensingAgent:
    """Get a SensingAgent with a conic FieldOfView."""
    cfg = deepcopy(SENSOR_CONFIG)
    cfg["field_of_view"] = {"fov_shape": "conic"}
    prop_cfg = MagicMock()
    prop_cfg.station_keeping = False
    prop_cfg.sensor_realtime_propagation = True

    dynamics = create_autospec(TwoBody, instance=True)

    conic_sensor_agent = SensingAgent.fromConfig(
        SensingAgentConfig(**cfg),
        clock,
        dynamics,
        prop_cfg,
    )
    conic_sensor_agent.sensors.host.time = ScenarioTime(30)
    return conic_sensor_agent


@pytest.fixture(name="rectangular_sensor_agent")
def getRectangularFOVSensingAgent(clock: ScenarioClock) -> SensingAgent:
    """Get a SensingAgent with a rectangular FieldOfView."""
    cfg = deepcopy(SENSOR_CONFIG)
    cfg["sensor"]["field_of_view"] = {"fov_shape": "rectangular"}

    prop_cfg = MagicMock()
    prop_cfg.station_keeping = False
    prop_cfg.sensor_realtime_propagation = True

    dynamics = create_autospec(TwoBody, instance=True)

    rectangular_sensor_agent = SensingAgent.fromConfig(
        SensingAgentConfig(**cfg),
        clock,
        dynamics,
        prop_cfg,
    )
    rectangular_sensor_agent.sensors.host.time = ScenarioTime(30)
    return rectangular_sensor_agent


@pytest.fixture(name="ukf")
def getUKF() -> UnscentedKalmanFilter:
    """Get an UnscentedKalmanFilter."""
    return UnscentedKalmanFilter(
        10001,
        0.0,
        zeros((6,)),
        zeros((6, 6)),
        TwoBody(),
        zeros((6, 6)),
        StandardNis(0.01),
        None,
    )


@pytest.fixture(name="primary_rso")
def getEstimateAgent1(ukf: UnscentedKalmanFilter, clock: ScenarioClock) -> EstimateAgent:
    """Get an EstimateAgent."""
    return EstimateAgent(
        10001,
        "Primary RSO",
        "Spacecraft",
        clock,
        array([26111.6, 33076.1, 0, -2.41152, 1.9074, 0]),
        zeros((6, 6)),
        ukf,
        None,
        InitialOrbitDeterminationConfig(),
        25.0,
        100.0,
        0.21,
    )


@pytest.fixture(name="secondary_rso")
def getEstimateAgent2(ukf: UnscentedKalmanFilter, clock: ScenarioClock) -> EstimateAgent:
    """Get an EstimateAgent."""
    return EstimateAgent(
        10002,
        "Secondary RSO",
        "Spacecraft",
        clock,
        array([26111.5, 33076.1, 0, -2.41153, 1.9074, 0]),
        zeros((6, 6)),
        ukf,
        None,
        InitialOrbitDeterminationConfig(),
        25.0,
        100.0,
        0.21,
    )


def testCanSlew(conic_sensor_agent: SensingAgent):
    """Test if you can slew to an RSO."""
    good_slant = array(
        [
            2.29494590e03,
            4.08271784e04,
            3.91179470e03,
            2.07249105e-04,
            -6.64332739e-05,
            2.16300407e-04,
        ],
    )
    val = conic_sensor_agent.sensors.canSlew(good_slant)
    assert bool(val) is True


def testCheckTargetsInView(
    clock: ScenarioClock,
    primary_rso: EstimateAgent,
    secondary_rso: EstimateAgent,
    conic_sensor_agent: SensingAgent,
):
    """Test if multiple targets are in the Field of View."""
    pointing_sez = getSlantRangeVector(
        conic_sensor_agent.sensors.host.eci_state,
        primary_rso.eci_state,
        clock.datetime_epoch,
    )
    primary_rso_sez = getSlantRangeVector(
        conic_sensor_agent.eci_state,
        primary_rso.eci_state,
        conic_sensor_agent.datetime_epoch,
    )
    secondary_rso_sez = getSlantRangeVector(
        conic_sensor_agent.eci_state,
        secondary_rso.eci_state,
        conic_sensor_agent.datetime_epoch,
    )
    agents = [
        conic_sensor_agent.sensors.field_of_view.inFieldOfView(pointing_sez, slant_range_sez)
        for slant_range_sez in (primary_rso_sez, secondary_rso_sez)
    ]
    assert len(agents) == 2


def testInFieldOfView(
    primary_rso: EstimateAgent,
    secondary_rso: EstimateAgent,
    conic_sensor_agent: SensingAgent,
    rectangular_sensor_agent: SensingAgent,
):
    """Test observations of two RSO with a single sensor at one time."""
    in_fov = conic_sensor_agent.sensors.field_of_view.inFieldOfView(
        primary_rso.eci_state[:3],
        secondary_rso.eci_state[:3],
    )
    assert bool(in_fov) is True
    not_in_fov = conic_sensor_agent.sensors.field_of_view.inFieldOfView(
        primary_rso.eci_state[:3],
        array([0, 0.01, 0]),
    )
    assert bool(not_in_fov) is False

    rectangle_in_fov = rectangular_sensor_agent.sensors.field_of_view.inFieldOfView(
        primary_rso.eci_state[:3],
        secondary_rso.eci_state[:3],
    )
    assert bool(rectangle_in_fov) is True
