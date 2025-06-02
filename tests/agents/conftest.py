"""Agents conftest."""

from __future__ import annotations

# Standard Library Imports
from datetime import datetime
from unittest.mock import create_autospec

# Third Party Imports
import numpy as np
import pytest

# RESONAATE Imports
from resonaate.agents.estimate_agent import EstimateAgent
from resonaate.agents.sensing_agent import SensingAgent
from resonaate.data.observation import Observation
from resonaate.dynamics.terrestrial import Terrestrial
from resonaate.dynamics.two_body import TwoBody
from resonaate.estimation.adaptive.adaptive_filter import AdaptiveFilter
from resonaate.estimation.adaptive.gpb1 import GeneralizedPseudoBayesian1
from resonaate.estimation.adaptive.mmae_stacking_utils import eciStack
from resonaate.estimation.kalman.unscented_kalman_filter import UnscentedKalmanFilter
from resonaate.estimation.maneuver_detection import StandardNis
from resonaate.physics.orbit_determination.lambert import lambertUniversal
from resonaate.physics.time.stardate import JulianDate, ScenarioTime
from resonaate.scenario.clock import ScenarioClock
from resonaate.scenario.config.estimation_config import (
    AdaptiveEstimationConfig,
    InitialOrbitDeterminationConfig,
)
from resonaate.sensors.advanced_radar import AdvRadar


@pytest.fixture(name="mocked_clock")
def getMockedScenarioClock() -> ScenarioClock:
    """Get a mocked :class:`.ScenarioClock` object."""
    mocked_clock = create_autospec(ScenarioClock, instance=True)
    mocked_clock.julian_date_start = JulianDate(2459304.0666666665)
    mocked_clock.datetime_start = datetime(2021, 3, 30, 13, 36)
    mocked_clock.julian_date_epoch = mocked_clock.julian_date_start
    mocked_clock.datetime_epoch = mocked_clock.datetime_start
    mocked_clock.julian_date_stop = mocked_clock.julian_date_start + (1 / 3)
    mocked_clock.initial_time = ScenarioTime(0.0)
    mocked_clock.time_span = ScenarioTime(28800.0)
    mocked_clock.time = ScenarioTime(0.0)
    mocked_clock.dt_step = ScenarioTime(300.0)
    return mocked_clock


@pytest.fixture(name="earth_sensor")
def getTestEarthSensor() -> AdvRadar:
    """Create a custom :class:`Agent` object for a sensor."""
    return AdvRadar(
        az_mask=np.array([0.0, 359.99999]),
        el_mask=np.array([1.0, 89.0]),
        r_matrix=np.diagflat([2.38820057e-11, 3.73156339e-11, 9.00000000e-08, 3.61000000e-10]),
        diameter=27.0,
        efficiency=0.9,
        field_of_view={"fov_shape": "conic"},
        background_observations=False,
        tx_power=120000.0,
        tx_frequency=10000000000.0,
        min_detectable_power=1.4314085925969573e-14,
        slew_rate=3.0000000000000004,
        detectable_vismag=25.0,
        minimum_range=0.0,
        maximum_range=99000,
    )


@pytest.fixture(name="sensor_agent")
def getTestSensorAgent(earth_sensor: AdvRadar, mocked_clock: ScenarioClock) -> SensingAgent:
    """Create a custom :class:`Agent` object for a sensor."""
    return SensingAgent(
        300000,
        "Test_sensor",
        "GroundFacility",
        np.array(
            [
                -1.55267475e03,
                1.47362430e03,
                5.98812597e03,
                -1.07453539e-01,
                -1.14109571e-01,
                2.19474290e-04,
            ],
        ),
        mocked_clock,
        earth_sensor,
        Terrestrial(
            JulianDate(2459304.1666666665),
            np.array(
                [
                    1.83995228e03,
                    1.11114727e03,
                    5.98497681e03,
                    1.16467265e-24,
                    -6.00704788e-24,
                    3.01869766e-18,
                ],
            ),
        ),
        True,
        10.0,
        100.0,
        0.21,
    )


@pytest.fixture(name="observations")
def getObservations(sensor_agent: SensingAgent) -> Observation:
    """Create a custom :class:`Observation` object for a sensor."""
    radar_observation = Observation(
        julian_date=JulianDate(2459304.267361111),
        sensor_id=300000,
        target_id=10001,
        sensor_type="AdvRadar",
        azimuth_rad=1.228134787553298,
        elevation_rad=0.5432822498364404,
        range_km=1953.3903221962914,
        range_rate_km_p_sec=-6.147282606743988,
        sensor_eci=sensor_agent.eci_state,
        measurement=sensor_agent.sensors.measurement,
    )

    return [radar_observation]


@pytest.fixture(name="nominal_filter")
def getNominalFilter() -> UnscentedKalmanFilter:
    """Create a :class:`.NominalFilter`."""
    return UnscentedKalmanFilter(
        tgt_id=10001,
        time=ScenarioTime(0.0),
        est_x=np.array([10000.0, 2.0, 10.0, 0.0, 7.0, 0.0]),
        est_p=np.diagflat(np.ones(6)),
        dynamics=TwoBody(),
        q_matrix=3 * np.diagflat(np.ones(6)),
        maneuver_detection=StandardNis(0.01),
        initial_orbit_determination=True,
    )


@pytest.fixture(name="estimate_agent")
def getTestEstimateAgent(
    nominal_filter: UnscentedKalmanFilter,
    mocked_clock: ScenarioClock,
) -> EstimateAgent:
    """Create a custom :class:.`Agent` object for testing."""
    return EstimateAgent(
        10001,
        "estimate_agent",
        "Spacecraft",
        mocked_clock,
        np.ones(6),
        np.diagflat(np.ones(6)),
        nominal_filter,
        None,
        None,
        10.0,
        100.0,
        0.21,
    )


@pytest.fixture(name="mmae_filter")
def getTestMMAEFilter(
    nominal_filter: UnscentedKalmanFilter,
    estimate_agent: EstimateAgent,
) -> AdaptiveFilter:
    """Create a :class:`.AdaptiveFilter`."""
    return GeneralizedPseudoBayesian1(
        nominal_filter=nominal_filter,
        timestep=estimate_agent.time,
        orbit_determination=lambertUniversal,
        stacking_method=eciStack,
        previous_obs_window=1,
        model_interval=600,
        prune_threshold=1e-10,
        prune_percentage=0.997,
    )


@pytest.fixture(name="mmae_estimate_agent")
def getTestMMAEEstimateAgent(
    mocked_clock: ScenarioClock,
    mmae_filter: AdaptiveFilter,
) -> EstimateAgent:
    """Create a custom :class:.`Agent` object for testing."""
    return EstimateAgent(
        _id=10001,
        name="estimate_agent",
        agent_type="Spacecraft",
        clock=mocked_clock,
        initial_state=np.ones(6),
        initial_covariance=np.diagflat(np.ones(6)),
        _filter=mmae_filter,
        adaptive_filter_config=AdaptiveEstimationConfig(
            name="gpb1",
            orbit_determination="lambert_universal",
            stacking_method="eci_stack",
            model_interval=600,
            observation_window=1,
            prune_threshold=1e-10,
            prune_percentage=0.997,
            parameters={},
        ),
        initial_orbit_determination_config=None,
        visual_cross_section=10.0,
        mass=100.0,
        reflectivity=0.21,
    )


@pytest.fixture(name="iod_estimate_agent")
def getTestIODEstimateAgent(
    mocked_clock: ScenarioClock,
    nominal_filter: UnscentedKalmanFilter,
) -> EstimateAgent:
    """Create a custom :class:.`Agent` object for testing."""
    nominal_filter.maneuver_detected = True

    return EstimateAgent(
        _id=10001,
        name="estimate_agent",
        agent_type="Spacecraft",
        clock=mocked_clock,
        initial_state=np.ones(6),
        initial_covariance=np.diagflat(np.ones(6)),
        _filter=nominal_filter,
        initial_orbit_determination_config=InitialOrbitDeterminationConfig(),
        adaptive_filter_config=None,
        visual_cross_section=10.0,
        mass=100.0,
        reflectivity=0.21,
    )
