"""Test :class:`.EstimateAgent`."""
# pylint:disable=unused-argument
from __future__ import annotations

# Standard Library Imports
from datetime import datetime
from unittest.mock import create_autospec

# Third Party Imports
import numpy as np
import pytest

# RESONAATE Imports
import resonaate.estimation.initial_orbit_determination
from resonaate.agents.estimate_agent import EstimateAgent
from resonaate.agents.sensing_agent import SensingAgent
from resonaate.data.observation import Observation
from resonaate.dynamics.terrestrial import Terrestrial
from resonaate.dynamics.two_body import TwoBody
from resonaate.estimation import initialOrbitDeterminationFactory
from resonaate.estimation.maneuver_detection import StandardNis
from resonaate.estimation.sequential.unscented_kalman_filter import UnscentedKalmanFilter
from resonaate.physics.time.stardate import JulianDate, ScenarioTime
from resonaate.scenario.clock import ScenarioClock
from resonaate.scenario.config.estimation_config import InitialOrbitDeterminationConfig
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
    earth_sensor = AdvRadar(
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
    return earth_sensor


@pytest.fixture(name="sensor_agent")
def getTestSensorAgent(earth_sensor: AdvRadar, mocked_clock: ScenarioClock) -> SensingAgent:
    """Create a custom :class:`Agent` object for a sensor."""
    sensor_agent = SensingAgent(
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
            ]
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
                ]
            ),
        ),
        True,
        10.0,
        100.0,
        0.21,
    )
    return sensor_agent


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
        sen_eci_state=sensor_agent.eci_state,
        measurement=sensor_agent.sensors.measurement,
    )

    return [radar_observation]


@pytest.fixture(name="nominal_filter")
def getNominalFilter() -> UnscentedKalmanFilter:
    """Create a :class:`.NominalFilter`."""
    nominal_filter = UnscentedKalmanFilter(
        10001,
        ScenarioTime(0.0),
        np.array([6378.0, 2.0, 10.0, 0.0, 7.0, 0.0]),
        np.diagflat([1.0, 2.0, 1.0, 1, 1, 1]),
        TwoBody(),
        3 * np.diagflat([1.0, 2.0, 1.0, 1, 1, 1]),
        StandardNis(0.01),
        True,
    )
    nominal_filter.maneuver_detected = True
    return nominal_filter


@pytest.fixture(name="estimate_agent")
def getTestEstimateAgent(
    nominal_filter: UnscentedKalmanFilter,
    mocked_clock: ScenarioClock,
) -> EstimateAgent:
    """Create a custom :class:.`Agent` object for testing."""
    estimate_agent = EstimateAgent(
        10001,
        "estimate_agent",
        "Spacecraft",
        mocked_clock,
        np.array(
            [
                4.38022237e03,
                -5.70920771e01,
                -5.29317945e03,
                -5.76471671e00,
                -1.46542677e00,
                -4.75396773e00,
            ]
        ),
        np.diagflat([1.0, 2.0, 1.0, 1, 1, 1]),
        nominal_filter,
        None,
        None,
        10.0,
        100.0,
        0.21,
    )
    return estimate_agent


def testAttemptInitialOrbitDetermination(
    estimate_agent: EstimateAgent,
    observations: Observation,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
):
    """Test _attemptInitialOrbitDetermination().

    Args:
        estimate_agent (:class:`.EstimateAgent`): Estimate agent fixture
        observations (:class:`.Observation`): Observation tuple fixture
        monkeypatch (``:class:`.MonkeyPatch``): patch of function
        caplog (:class:`.LogCaptureFixture`): logging of function calls
    """
    # pylint:disable=protected-access
    original_state = estimate_agent.nominal_filter.est_x.copy()
    # Test the quick return
    estimate_agent._attemptInitialOrbitDetermination(observations)
    assert estimate_agent.iod_start_time is None

    # Test setting the start time
    iod_config = InitialOrbitDeterminationConfig()
    estimate_agent.initial_orbit_determination = initialOrbitDeterminationFactory(
        iod_config, estimate_agent.simulation_id, estimate_agent.julian_date_start
    )
    estimate_agent._attemptInitialOrbitDetermination(observations)
    assert estimate_agent.iod_start_time == ScenarioTime(0.0)

    # Test unsuccessful IOD
    estimate_agent.time = ScenarioTime(300.0)
    bad_state = np.array([1, 2, 3, 4, 5, 7])

    def determineNewEstimateStateBad(
        self, observations, detection_time, current_time
    ):  # pylint:disable=unused-argument
        return bad_state, False

    with monkeypatch.context() as m_patch:
        m_patch.setattr(
            resonaate.estimation.initial_orbit_determination.LambertIOD,
            "determineNewEstimateState",
            determineNewEstimateStateBad,
        )
        estimate_agent._attemptInitialOrbitDetermination(observations)
        assert np.allclose(estimate_agent.nominal_filter.est_x, original_state)
        assert not np.allclose(estimate_agent.nominal_filter.est_x, bad_state)
        assert estimate_agent.iod_start_time == ScenarioTime(0.0)

    # Test successful IOD
    good_state = np.array([1, 2, 3, 4, 5, 6])

    def determineNewEstimateStateGood(self, observations, detection_time, current_time):
        return good_state, True

    with monkeypatch.context() as m_patch:
        m_patch.setattr(
            resonaate.estimation.initial_orbit_determination.LambertIOD,
            "determineNewEstimateState",
            determineNewEstimateStateGood,
        )
        estimate_agent._attemptInitialOrbitDetermination(observations)
        assert not np.allclose(estimate_agent.nominal_filter.est_x, original_state)
        assert np.allclose(estimate_agent.nominal_filter.est_x, good_state)
        assert estimate_agent.iod_start_time is None
