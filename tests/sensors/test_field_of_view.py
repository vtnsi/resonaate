# pylint: disable=unused-argument
from __future__ import annotations

# Standard Library Imports
from copy import deepcopy
from datetime import datetime

# Third Party Imports
import pytest
from numpy import array, zeros

# RESONAATE Imports
from resonaate.agents.estimate_agent import EstimateAgent
from resonaate.agents.sensing_agent import SensingAgent
from resonaate.dynamics.two_body import TwoBody
from resonaate.estimation.maneuver_detection import StandardNis
from resonaate.estimation.sequential.unscented_kalman_filter import UnscentedKalmanFilter
from resonaate.physics.time.stardate import ScenarioTime
from resonaate.physics.transforms.methods import getSlantRangeVector
from resonaate.physics.transforms.reductions import updateReductionParameters
from resonaate.scenario.clock import ScenarioClock
from resonaate.scenario.config.agent_configs import SensingAgentConfig
from resonaate.scenario.config.estimation_config import InitialOrbitDeterminationConfig

SENSOR_CONFIG = {
    "name": "Test Radar",
    "id": 200000,
    "covariance": [
        [3.0461741978670863e-12, 0.0, 0.0, 0.0],
        [0.0, 3.0461741978670863e-12, 0.0, 0.0],
        [0.0, 0.0, 2.5000000000000004e-11, 0.0],
        [0.0, 0.0, 0.0, 4.0000000000000015e-12],
    ],
    "slew_rate": 0.08726646259971647,
    "azimuth_range": [0.0, 6.283185132646661],
    "elevation_range": [0.017453292519943295, 1.5707961522619713],
    "efficiency": 0.95,
    "aperture_area": 530.929158456675,
    "sensor_type": "Radar",
    "background_observations": True,
    "lat": 0.2281347875532986,
    "lon": 0.5432822498364406,
    "alt": 0.095,
    "host_type": "GroundFacility",
    "tx_power": 2.5e6,
    "tx_frequency": 1.5e9,
    "min_detectable_power": 1.4314085925969573e-14,
}


@pytest.fixture(name="clock")
def getScenarioClock(reset_shared_db: None) -> ScenarioClock:
    """Get a ScenarioClock."""
    start_date = datetime(2020, 6, 6, 0, 0)
    return ScenarioClock(start_date, 60.0, 30.0)


@pytest.fixture(name="conic_sensor_agent")
def getConicFOVSensingAgent(clock: ScenarioClock) -> SensingAgent:
    """Get a SensingAgent with a conic FieldOfView."""
    cfg = deepcopy(SENSOR_CONFIG)
    cfg["field_of_view"] = {"fov_shape": "conic"}
    conic_sensor_config = {
        "agent": SensingAgentConfig(**SENSOR_CONFIG),
        "realtime": True,
        "clock": clock,
    }
    conic_sensor_agent = SensingAgent.fromConfig(conic_sensor_config)
    conic_sensor_agent.sensors.host.time = ScenarioTime(30)
    return conic_sensor_agent


@pytest.fixture(name="rectangular_sensor_agent")
def getRectangularFOVSensingAgent(clock: ScenarioClock) -> SensingAgent:
    """Get a SensingAgent with a rectangular FieldOfView."""
    cfg = deepcopy(SENSOR_CONFIG)
    cfg["field_of_view"] = {"fov_shape": "rectangular"}
    rectangular_sensor_config = {
        "agent": SensingAgentConfig(**cfg),
        "realtime": True,
        "clock": clock,
    }
    rectangular_sensor_agent = SensingAgent.fromConfig(rectangular_sensor_config)
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
        ]
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
    updateReductionParameters(clock.datetime_epoch)
    slant_range_sez = getSlantRangeVector(
        conic_sensor_agent.sensors.host.ecef_state, primary_rso.eci_state
    )
    agents = conic_sensor_agent.sensors.checkTargetsInView(
        slant_range_sez, [primary_rso, secondary_rso]
    )
    assert len(agents) == 2


def testInFieldOfView(
    primary_rso: EstimateAgent,
    secondary_rso: EstimateAgent,
    conic_sensor_agent: SensingAgent,
    rectangular_sensor_agent: SensingAgent,
):
    """Test observations of two RSO with a single sensor at one time."""
    in_fov = conic_sensor_agent.sensors.field_of_view.inFieldOfView(
        primary_rso.eci_state[:3], secondary_rso.eci_state[:3]
    )
    assert bool(in_fov) is True
    not_in_fov = conic_sensor_agent.sensors.field_of_view.inFieldOfView(
        primary_rso.eci_state[:3], array([0, 0.01, 0])
    )
    assert bool(not_in_fov) is False

    rectangle_in_fov = rectangular_sensor_agent.sensors.field_of_view.inFieldOfView(
        primary_rso.eci_state[:3], secondary_rso.eci_state[:3]
    )
    assert bool(rectangle_in_fov) is True
