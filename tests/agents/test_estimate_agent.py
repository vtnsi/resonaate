"""Test :class:`.EstimateAgent`."""

# pylint:disable=unused-argument
from __future__ import annotations

# Standard Library Imports
from datetime import datetime
from typing import Any
from unittest.mock import create_autospec

# Third Party Imports
import numpy as np
import pytest
from numpy import array, float64

# RESONAATE Imports
import resonaate.estimation.initial_orbit_determination
from resonaate.agents.estimate_agent import EstimateAgent
from resonaate.agents.sensing_agent import SensingAgent
from resonaate.common.exceptions import ShapeError
from resonaate.common.utilities import getTypeString
from resonaate.data.observation import Observation
from resonaate.dynamics.terrestrial import Terrestrial
from resonaate.dynamics.two_body import TwoBody
from resonaate.estimation.adaptive.adaptive_filter import AdaptiveFilter
from resonaate.estimation.adaptive.gpb1 import GeneralizedPseudoBayesian1
from resonaate.estimation.initial_orbit_determination import IODSolution
from resonaate.estimation.maneuver_detection import StandardNis
from resonaate.estimation.sequential.sequential_filter import FilterFlag
from resonaate.estimation.sequential.unscented_kalman_filter import UnscentedKalmanFilter
from resonaate.physics.time.stardate import JulianDate, ScenarioTime
from resonaate.physics.transforms.methods import eci2ecef
from resonaate.scenario.clock import ScenarioClock
from resonaate.scenario.config.estimation_config import AdaptiveEstimationConfig
from resonaate.sensors.advanced_radar import AdvRadar

# pylint: disable=protected-access
pytestmark = pytest.mark.usefixtures("database")


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
    six_by_six_matrix = np.diagflat([1.0, 2.0, 1.0, 1, 1, 1])
    return UnscentedKalmanFilter(
        tgt_id=10001,
        time=ScenarioTime(0.0),
        est_x=np.array([10000.0, 2.0, 10.0, 0.0, 7.0, 0.0]),
        est_p=six_by_six_matrix,
        dynamics=TwoBody(),
        q_matrix=3 * six_by_six_matrix,
        maneuver_detection=StandardNis(0.01),
        initial_orbit_determination=True,
    )


@pytest.fixture(name="async_result_predict")
def getAsyncResultPredict() -> dict[str, Any]:
    """Get async_result prediction data."""
    return {
        "time": ScenarioTime(300.0),
        "est_x": np.ones(6),
        "est_p": np.ones((6, 6)),
        "pred_x": np.ones(6),
        "pred_p": np.ones((6, 6)),
        "sigma_points": np.ones((6, 13)),
        "sigma_x_res": np.ones((6, 13)),
    }


@pytest.fixture(name="async_result_update")
def getAsyncResultUpdate() -> dict[str, Any]:
    """Get async_result update data."""
    return {
        "estimate_id": 20001,
        "filter_update": {
            "is_angular": array([], dtype=float64),
            "mean_pred_y": array([], dtype=float64),
            "r_matrix": array([], dtype=float64),
            "cross_cvr": array([], dtype=float64),
            "innov_cvr": array([], dtype=float64),
            "kalman_gain": array([], dtype=float64),
            "est_p": np.ones((6, 6)),
            "sigma_points": np.ones((6, 13)),
            "sigma_y_res": array([], dtype=float64),
            "est_x": np.ones(6),
            "innovation": array([], dtype=float64),
            "nis": array([], dtype=float64),
            "source": "Propagation",
            "maneuver_metric": None,
            "maneuver_detected": False,
        },
        "observations": [],
        "observed": False,
        "new_filter": None,
    }


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


def testEstimateAgentGoodInit(nominal_filter: UnscentedKalmanFilter, mocked_clock: ScenarioClock):
    """Test EstimateAgent init and edge cases.

    Args:
        nominal_filter (:class:`.UnscentedKalmanFilter`): UKF Object
        mocked_clock (:class:`.ScenarioClock`): Mocked Scenario Clock
    """
    estimate_agent_good = EstimateAgent(
        10001,
        "estimate_agent",
        "Spacecraft",
        mocked_clock,
        np.ones(6),
        np.ones((6, 6)),
        nominal_filter,
        None,
        None,
        10.0,
        100.0,
        0.21,
    )
    assert isinstance(estimate_agent_good, EstimateAgent)


def testEstimateAgentBadCovarianceInit(
    nominal_filter: UnscentedKalmanFilter, mocked_clock: ScenarioClock
):
    """Test EstimateAgent with bad covariance shape.

    Args:
        nominal_filter (:class:`.UnscentedKalmanFilter`): UKF Object
        mocked_clock (:class:`.ScenarioClock`): Mocked Scenario Clock
    """
    bad_covariance = np.ones((5, 6))
    with pytest.raises(ShapeError):
        _ = EstimateAgent(
            10001,
            "estimate_agent",
            "Spacecraft",
            mocked_clock,
            np.ones(6),
            bad_covariance,
            nominal_filter,
            None,
            None,
            10.0,
            100.0,
            0.21,
        )


def testEstimateAgentBadSeedInit(
    nominal_filter: UnscentedKalmanFilter, mocked_clock: ScenarioClock
):
    """Test EstimateAgent with bad seed shape.

    Args:
        nominal_filter (:class:`.UnscentedKalmanFilter`): UKF Object
        mocked_clock (:class:`.ScenarioClock`): Mocked Scenario Clock
    """
    bad_seed_type = 1.0
    with pytest.raises(TypeError):
        _ = EstimateAgent(
            10001,
            "estimate_agent",
            "Spacecraft",
            mocked_clock,
            np.ones(6),
            np.ones((6, 6)),
            nominal_filter,
            None,
            None,
            10.0,
            100.0,
            0.21,
            bad_seed_type,
        )


def testEstimateAgentBadFilterInit(mocked_clock: ScenarioClock):
    """Test EstimateAgent with bad filter shape.

    Args:
        mocked_clock (:class:`.ScenarioClock`): Mocked Scenario Clock
    """

    # Bad Filter type
    class BadFilterObject:
        dynamics = TwoBody()

    with pytest.raises(TypeError):
        _ = EstimateAgent(
            10001,
            "estimate_agent",
            "Spacecraft",
            mocked_clock,
            np.ones(6),
            np.ones((6, 6)),
            BadFilterObject,
            None,
            None,
            10.0,
            100.0,
            0.21,
        )


def testUpdateEstimateNoObservations(estimate_agent: EstimateAgent, observations: Observation):
    """Test updateEstimate without observations.

    Args:
        estimate_agent (:class:`.EstimateAgent`): Estimate agent fixture
        observations (:class:`.Observation`): Observation tuple fixture
    """
    estimate_agent.nominal_filter.predict(ScenarioTime(60.0))
    estimate_agent.nominal_filter.forecast(observations)
    estimate_agent.updateEstimate([])

    assert np.allclose(estimate_agent.state_estimate, estimate_agent.nominal_filter.est_x)
    assert np.allclose(estimate_agent.error_covariance, estimate_agent.nominal_filter.est_p)


def testUpdateEstimateWithObservations(estimate_agent: EstimateAgent, observations: Observation):
    """Test updateEstimate without observations.

    Args:
        estimate_agent (:class:`.EstimateAgent`): Estimate agent fixture
        observations (:class:`.Observation`): Observation tuple fixture
    """
    estimate_agent.nominal_filter.predict(ScenarioTime(60.0))
    estimate_agent.nominal_filter.forecast(observations)
    estimate_agent.updateEstimate(observations)

    assert np.allclose(estimate_agent.state_estimate, estimate_agent.nominal_filter.est_x)
    assert np.allclose(estimate_agent.error_covariance, estimate_agent.nominal_filter.est_p)


def testUpdateFromAsyncPredict(
    estimate_agent: EstimateAgent, observations: Observation, async_result_predict: dict
):
    """Test updateEstimate without observations.

    Args:
        estimate_agent (:class:`.EstimateAgent`): Estimate agent fixture
        observations (:class:`.Observation`): Observation tuple fixture
        async_result_predict (``dict``): Dict of IOD init async prediction
    """
    estimate_agent.nominal_filter.predict(ScenarioTime(60.0))
    estimate_agent.nominal_filter.forecast(observations)
    estimate_agent.updateFromAsyncPredict(async_result_predict)
    assert np.allclose(estimate_agent.state_estimate, estimate_agent.nominal_filter.pred_x)
    assert np.allclose(estimate_agent.error_covariance, estimate_agent.nominal_filter.pred_p)


def testUpdateFromAsyncUpdateEstimate(
    estimate_agent: EstimateAgent, observations: Observation, async_result_update: dict
):
    """Test updateEstimate without observations.

    Args:
        estimate_agent (:class:`.EstimateAgent`): Estimate agent fixture
        observations (:class:`.Observation`): Observation tuple fixture
        async_result_update (``dict``): Dict of IOD init async update
    """
    estimate_agent.nominal_filter.predict(ScenarioTime(60.0))
    estimate_agent.nominal_filter.forecast(observations)
    estimate_agent.updateFromAsyncUpdateEstimate(async_result_update)
    assert np.allclose(estimate_agent.state_estimate, estimate_agent.nominal_filter.est_x)
    assert np.allclose(estimate_agent.error_covariance, estimate_agent.nominal_filter.est_p)


def testGetCurrentEphemeris(estimate_agent: EstimateAgent):
    """Test getCurrentEphemeris.

    Args:
        estimate_agent (:class:`.EstimateAgent`): Estimate agent fixture
    """
    ephem = estimate_agent.getCurrentEphemeris()

    assert ephem.agent_id == estimate_agent.simulation_id
    assert ephem.julian_date == estimate_agent.julian_date_epoch
    assert ephem.source == estimate_agent.nominal_filter.source
    assert ephem.eci == estimate_agent.eci_state.tolist()
    assert ephem.covariance == estimate_agent.error_covariance.tolist()


def testSaveDetectedManeuver(estimate_agent: EstimateAgent, observations: Observation):
    """Test _saveDetectedManeuver.

    Args:
        estimate_agent (:class:`.EstimateAgent`): Estimate agent fixture
        observations (:class:`.Observation`): Observation tuple fixture
    """
    nis = 130574.36952388566
    estimate_agent.nominal_filter.predict(ScenarioTime(60.0))
    estimate_agent.nominal_filter.forecast(observations)
    estimate_agent.nominal_filter.nis = nis
    estimate_agent.nominal_filter.maneuver_metric = nis
    estimate_agent.nominal_filter.maneuver_detection.metric = nis
    estimate_agent._saveDetectedManeuver(observations)
    detection = estimate_agent._detected_maneuvers[0]

    assert detection.julian_date == estimate_agent.julian_date_epoch
    assert detection.sensor_ids == str(observations[0].sensor_id)
    assert detection.target_id == estimate_agent.simulation_id
    assert detection.nis == estimate_agent.nominal_filter.nis
    assert detection.method == getTypeString(estimate_agent.nominal_filter.maneuver_detection)
    assert detection.metric == estimate_agent.nominal_filter.maneuver_metric
    assert detection.threshold == estimate_agent.nominal_filter.maneuver_detection.threshold


def testGetDetectedManeuvers(estimate_agent: EstimateAgent, observations: Observation):
    """Test getDetectedManeuvers.

    Args:
        estimate_agent (:class:`.EstimateAgent`): Estimate agent fixture
        observations (:class:`.Observation`): Observation tuple fixture
    """
    nis = 130574.36952388566
    estimate_agent.nominal_filter.predict(ScenarioTime(60.0))
    estimate_agent.nominal_filter.forecast(observations)
    estimate_agent.nominal_filter.nis = nis
    estimate_agent.nominal_filter.maneuver_metric = nis
    estimate_agent.nominal_filter.maneuver_detection.metric = nis
    estimate_agent._saveDetectedManeuver(observations)
    detections = estimate_agent.getDetectedManeuvers()

    assert len(detections) == 1
    assert len(estimate_agent._detected_maneuvers) == 0


def testSaveFilterStep(estimate_agent: EstimateAgent, observations: Observation):
    """Test saveFilterStep.

    Args:
        estimate_agent (:class:`.EstimateAgent`): Estimate agent fixture
        observations (:class:`.Observation`): Observation tuple fixture
    """
    estimate_agent.nominal_filter.predict(ScenarioTime(60.0))
    estimate_agent.nominal_filter.forecast(observations)
    estimate_agent.updateEstimate(observations)

    estimate_agent._saveFilterStep()
    info = estimate_agent._filter_info[0]

    assert info.julian_date == estimate_agent.julian_date_epoch
    assert info.target_id == estimate_agent.simulation_id
    assert np.allclose(info.innovation, estimate_agent.nominal_filter.innovation)
    assert info.nis == estimate_agent.nominal_filter.nis


def testGestFilterSteps(estimate_agent: EstimateAgent, observations: Observation):
    """Test getFilterSteps.

    Args:
        estimate_agent (:class:`.EstimateAgent`): Estimate agent fixture
        observations (:class:`.Observation`): Observation tuple fixture
    """

    estimate_agent.nominal_filter.predict(ScenarioTime(60.0))
    estimate_agent.nominal_filter.forecast(observations)
    estimate_agent.updateEstimate(observations)

    step = estimate_agent.getFilterSteps()

    assert len(step) == 1
    assert len(estimate_agent._filter_info) == 0


def testUpdateNoManeuverDetected(estimate_agent: EstimateAgent, observations: Observation):
    """Test _update without a maneuver detection.

    Args:
        estimate_agent (:class:`.EstimateAgent`): Estimate agent fixture
        observations (:class:`.Observation`): Observation tuple fixture
    """
    estimate_agent.nominal_filter.predict(ScenarioTime(60.0))
    estimate_agent.nominal_filter.forecast(observations)
    estimate_agent.nominal_filter.update(observations)
    estimate_agent.nominal_filter.maneuver_detected = False

    # Update with a maneuver detection
    estimate_agent._update(observations)
    assert len(estimate_agent._detected_maneuvers) == 0
    assert np.allclose(estimate_agent.state_estimate, estimate_agent.nominal_filter.est_x)
    assert np.allclose(estimate_agent.error_covariance, estimate_agent.nominal_filter.est_p)


def testUpdateManeuverDetected(estimate_agent: EstimateAgent, observations: Observation):
    """Test _update with a maneuver detection.

    Args:
        estimate_agent (:class:`.EstimateAgent`): Estimate agent fixture
        observations (:class:`.Observation`): Observation tuple fixture
    """
    estimate_agent.nominal_filter.predict(ScenarioTime(60.0))
    estimate_agent.nominal_filter.forecast(observations)
    estimate_agent.nominal_filter.update(observations)
    estimate_agent.nominal_filter.maneuver_detected = True

    # Update with a maneuver detection
    estimate_agent._update(observations)
    assert len(estimate_agent._detected_maneuvers) == 1
    assert np.allclose(estimate_agent.state_estimate, estimate_agent.nominal_filter.est_x)
    assert np.allclose(estimate_agent.error_covariance, estimate_agent.nominal_filter.est_p)


def testUpdateSuccessfulIOD(
    iod_estimate_agent: EstimateAgent,
    observations: Observation,
    monkeypatch: pytest.MonkeyPatch,
):
    """Test _update with successful IOD.

    Args:
        iod_estimate_agent (:class:`.EstimateAgent`): Estimate agent fixture with IOD on.
        observations (:class:`.Observation`): Observation tuple fixture
        monkeypatch (``:class:`.MonkeyPatch``): patch of function
    """
    iod_estimate_agent.nominal_filter.predict(ScenarioTime(60.0))
    iod_estimate_agent.nominal_filter.forecast(observations)
    iod_estimate_agent.nominal_filter.update(observations)
    iod_estimate_agent.nominal_filter.maneuver_detected = True

    # Patch IOD logic
    def mockIOD(self, observations, logging):
        return True, iod_estimate_agent.state_estimate

    monkeypatch.setattr(
        EstimateAgent,
        "_attemptInitialOrbitDetermination",
        mockIOD,
    )
    # Update with a maneuver detection
    iod_estimate_agent._update(observations)

    # Step forward a minute
    iod_estimate_agent.time = ScenarioTime(120.0)
    iod_estimate_agent._update(observations)

    assert iod_estimate_agent.iod_start_time is None


def testUpdateAdaptiveFilterNoManeuverDetection(
    estimate_agent: EstimateAgent,
    observations: Observation,
):
    """Test _update of a closing MMAE filter.

    Args:
        estimate_agent (:class:`.EstimateAgent`): Estimate agent fixture.
        observations (:class:`.Observation`): Observation tuple fixture
    """
    estimate_agent.nominal_filter.predict(ScenarioTime(60.0))
    estimate_agent.nominal_filter.forecast(observations)
    estimate_agent.nominal_filter.update(observations)
    estimate_agent.nominal_filter.maneuver_detected = False

    # Update with a maneuver detection
    estimate_agent._update(observations)

    assert isinstance(estimate_agent.nominal_filter, UnscentedKalmanFilter)


def testUpdateAttemptAdaptiveEstimation(
    nominal_filter: UnscentedKalmanFilter,
    mocked_clock: ScenarioClock,
    observations: Observation,
):
    """Test _attemptAdaptiveEstimation.

    Args:
        nominal_filter (:class:`.UnscentedKalmanFilter`): UKF Object
        mocked_clock (:class:`.ScenarioClock`): Mocked Scenario Clock
        observations (:class:`.Observation`): Observation tuple fixture
    """
    mmae_estimate_agent = EstimateAgent(
        _id=10001,
        name="estimate_agent",
        agent_type="Spacecraft",
        clock=mocked_clock,
        initial_state=np.ones(6),
        initial_covariance=np.diagflat(np.ones(6)),
        _filter=nominal_filter,
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
    mmae_estimate_agent.nominal_filter.maneuver_detected = True

    mmae_estimate_agent.nominal_filter.predict(ScenarioTime(60.0))
    mmae_estimate_agent.nominal_filter.forecast(observations)
    mmae_estimate_agent.nominal_filter.update(observations)

    # Update with a maneuver detection
    mmae_estimate_agent._update(observations)

    assert isinstance(mmae_estimate_agent.nominal_filter, UnscentedKalmanFilter)


def testAttemptAdaptiveEstimation(
    mmae_filter: AdaptiveFilter,
    observations: Observation,
    mocked_clock: ScenarioClock,
    monkeypatch: pytest.MonkeyPatch,
):
    """Test _attemptAdaptiveEstimation.

    Args:
        mmae_filter (:class:`.AdaptiveFilter`): MMAE Object
        observations (:class:`.Observation`): Observation tuple fixture
        mocked_clock (:class:`.ScenarioClock`): Mocked Scenario Clock
        monkeypatch (class:`.MonkeyPatch`): Pytest patch function
    """
    mmae_filter.flags = FilterFlag.ADAPTIVE_ESTIMATION_START

    mmae_estimate_agent = EstimateAgent(
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

    mmae_estimate_agent._beginAdaptiveEstimation(observations)

    assert mmae_estimate_agent.nominal_filter == mmae_filter

    # Reset flag
    mmae_estimate_agent.nominal_filter.flags = FilterFlag.ADAPTIVE_ESTIMATION_START

    # Patch `mmae_started` variable
    def mockInitialize(*args, **kwargs):
        return True

    monkeypatch.setattr(GeneralizedPseudoBayesian1, "initialize", mockInitialize)

    mmae_estimate_agent._beginAdaptiveEstimation(observations)

    assert mmae_estimate_agent.nominal_filter != mmae_filter


def testBeginInitialOrbitDeterminationReturn(estimate_agent: EstimateAgent):
    """Test _beginInitialOrbitDetermination returns if no IOD set.

    Args:
        estimate_agent (:class:`.EstimateAgent`): Estimate agent fixture
    """
    estimate_agent._beginInitialOrbitDetermination()

    assert estimate_agent.iod_start_time is None


def testBeginInitialOrbitDeterminationContinue(iod_estimate_agent: EstimateAgent):
    """Test _beginInitialOrbitDetermination sets iod start time.

    Args:
        iod_estimate_agent (:class:`.EstimateAgent`): Estimate agent fixture with IOD on.
    """
    iod_estimate_agent.nominal_filter.maneuver_detected = False
    iod_estimate_agent._beginInitialOrbitDetermination()

    assert iod_estimate_agent.iod_start_time is None


def testBeginInitialOrbitDeterminationSuccess(iod_estimate_agent: EstimateAgent):
    """Test _beginInitialOrbitDetermination sets iod start time.

    Args:
        iod_estimate_agent (:class:`.EstimateAgent`): Estimate agent fixture with IOD on.
    """
    iod_estimate_agent._beginInitialOrbitDetermination()

    assert iod_estimate_agent.iod_start_time == iod_estimate_agent.time


def testBeginInitialOrbitDeterminationNoSuccess(
    iod_estimate_agent: EstimateAgent, observations: Observation
):
    """Test _beginInitialOrbitDetermination sets iod start time.

    Args:
        iod_estimate_agent (:class:`.EstimateAgent`): Estimate agent fixture with IOD on.
        observations (:class:`.Observation`): Observation tuple fixture
    """
    iod_estimate_agent.nominal_filter.predict(ScenarioTime(60.0))
    iod_estimate_agent.nominal_filter.forecast(observations)
    iod_estimate_agent.nominal_filter.update(observations)
    iod_estimate_agent._update(observations=observations)

    assert iod_estimate_agent.iod_start_time == iod_estimate_agent.time


def testNoAttemptInitialOrbitDetermination(
    estimate_agent: EstimateAgent, observations: Observation
):
    """Test _attemptInitialOrbitDetermination returns if no IOD set.

    Args:
        estimate_agent (:class:`.EstimateAgent`): Estimate agent fixture
        observations (:class:`.Observation`): Observation tuple fixture
    """
    result, message = estimate_agent._attemptInitialOrbitDetermination(observations)

    assert estimate_agent.initial_orbit_determination is None
    assert result is False
    assert message is None

    estimate_agent.initial_orbit_determination = True
    estimate_agent.iod_start_time = ScenarioTime(0.0)
    estimate_agent.time = ScenarioTime(0.0)

    result, message = estimate_agent._attemptInitialOrbitDetermination(observations)

    assert result is False
    assert message is None


def testAttemptInitialOrbitDeterminationFail(
    iod_estimate_agent: EstimateAgent,
    observations: Observation,
):
    """Test _attemptInitialOrbitDetermination with no success.

    Args:
        iod_estimate_agent (:class:`.EstimateAgent`): Estimate agent fixture with IOD on.
        observations (:class:`.Observation`): Observation tuple fixture
    """
    iod_estimate_agent._beginInitialOrbitDetermination()
    assert iod_estimate_agent.iod_start_time == ScenarioTime(0.0)

    # Test unsuccessful IOD
    iod_estimate_agent.time = ScenarioTime(300.0)
    fail, iod_state = iod_estimate_agent._attemptInitialOrbitDetermination(observations)

    assert fail is False
    assert iod_state is None


def testAttemptInitialOrbitDeterminationBadTime(
    iod_estimate_agent: EstimateAgent,
    observations: Observation,
):
    """Test _attemptInitialOrbitDetermination with a bad IOD start time.

    Args:
        iod_estimate_agent (:class:`.EstimateAgent`): Estimate agent fixture with IOD on.
        observations (:class:`.Observation`): Observation tuple fixture
    """
    iod_estimate_agent._beginInitialOrbitDetermination()
    assert iod_estimate_agent.iod_start_time == ScenarioTime(0.0)

    # Test unsuccessful IOD
    iod_estimate_agent.iod_start_time = ScenarioTime(3000.0)
    msg = r"IOD .*: ScenarioTime\(\d*.\d* seconds\) .*: ScenarioTime\(\d*.\d* seconds\)"
    with pytest.raises(ValueError, match=msg):
        _, _ = iod_estimate_agent._attemptInitialOrbitDetermination(observations)


def testAttemptInitialOrbitDeterminationSuccess(
    iod_estimate_agent: EstimateAgent,
    observations: Observation,
    monkeypatch: pytest.MonkeyPatch,
):
    """Test _attemptInitialOrbitDetermination with success.

    Args:
        iod_estimate_agent (:class:`.EstimateAgent`): Estimate agent fixture with IOD on.
        observations (:class:`.Observation`): Observation tuple fixture
        monkeypatch (``:class:`.MonkeyPatch``): patch of function
    """
    iod_estimate_agent._beginInitialOrbitDetermination()
    assert iod_estimate_agent.iod_start_time == ScenarioTime(0.0)

    iod_estimate_agent.time = ScenarioTime(300.0)

    # Patch IOD logic
    def determineNewEstimateStateGood(self, observations, detection_time, current_time):
        return IODSolution(
            state_vector=iod_estimate_agent.state_estimate, convergence=True, message=None
        )

    monkeypatch.setattr(
        resonaate.estimation.initial_orbit_determination.LambertIOD,
        "determineNewEstimateState",
        determineNewEstimateStateGood,
    )
    success, iod_state = iod_estimate_agent._attemptInitialOrbitDetermination(observations)

    assert success is True
    assert isinstance(iod_state, np.ndarray)


def testAttemptInitialOrbitDeterminationFailLogging(
    iod_estimate_agent: EstimateAgent,
    observations: Observation,
):
    """Test _attemptInitialOrbitDetermination with no success and logging on.

    Args:
        iod_estimate_agent (:class:`.EstimateAgent`): Estimate agent fixture with IOD on.
        observations (:class:`.Observation`): Observation tuple fixture
    """
    iod_estimate_agent._beginInitialOrbitDetermination()
    assert iod_estimate_agent.iod_start_time == ScenarioTime(0.0)

    # Test unsuccessful IOD
    iod_estimate_agent.time = ScenarioTime(300.0)
    fail, iod_state = iod_estimate_agent._attemptInitialOrbitDetermination(observations, True)

    assert fail is False
    assert iod_state is None


@pytest.mark.usefixtures("database")
def testAttemptInitialOrbitDeterminationSuccessLogging(
    iod_estimate_agent: EstimateAgent,
    observations: Observation,
    monkeypatch: pytest.MonkeyPatch,
):
    """Test _attemptInitialOrbitDetermination with success.

    Args:
        iod_estimate_agent (:class:`.EstimateAgent`): Estimate agent fixture with IOD on.
        observations (:class:`.Observation`): Observation tuple fixture
        monkeypatch (``:class:`.MonkeyPatch``): patch of function
    """
    iod_estimate_agent._beginInitialOrbitDetermination()
    assert iod_estimate_agent.iod_start_time == ScenarioTime(0.0)

    iod_estimate_agent.time = ScenarioTime(300.0)

    # Patch IOD logic
    def determineNewEstimateStateGood(self, observations, detection_time, current_time):
        return IODSolution(
            state_vector=iod_estimate_agent.state_estimate, convergence=True, message=None
        )

    monkeypatch.setattr(
        resonaate.estimation.initial_orbit_determination.LambertIOD,
        "determineNewEstimateState",
        determineNewEstimateStateGood,
    )
    success, iod_state = iod_estimate_agent._attemptInitialOrbitDetermination(
        observations=observations, logging=True
    )

    assert success is True
    assert isinstance(iod_state, np.ndarray)


def testResetFilterGood(estimate_agent: EstimateAgent):
    """Test resetFilter with a good filter.

    Args:
        estimate_agent (:class:`.EstimateAgent`): Estimate agent fixture
    """
    new_filter = UnscentedKalmanFilter(
        tgt_id=10001,
        time=ScenarioTime(0.0),
        est_x=np.array([10000.0, 2.0, 10.0, 0.0, 7.0, 0.0]),
        est_p=np.diagflat(np.ones(6)),
        dynamics=TwoBody(),
        q_matrix=3 * np.diagflat(np.ones(6)),
        maneuver_detection=StandardNis(0.001),
    )

    estimate_agent._resetFilter(new_filter)
    assert estimate_agent._filter is new_filter
    assert estimate_agent._filter.maneuver_detection.threshold == 0.001
    assert estimate_agent._filter.gamma == new_filter.gamma
    assert estimate_agent._filter.est_p[1, 1] == new_filter.est_p[1, 1]


def testResetFilterBad(estimate_agent: EstimateAgent):
    """Test resetFilter with a bad filter.

    Args:
        estimate_agent (:class:`.EstimateAgent`): Estimate agent fixture
    """
    with pytest.raises(TypeError):
        estimate_agent._resetFilter("Bad!")


def testProperties(estimate_agent: EstimateAgent):
    """Test properties.

    Args:
        estimate_agent (:class:`.EstimateAgent`): Estimate agent fixture
    """
    assert np.allclose(estimate_agent.eci_state, estimate_agent._state_estimate)
    assert np.allclose(estimate_agent.ecef_state, estimate_agent._ecef_state)
    assert np.allclose(estimate_agent.lla_state, estimate_agent._lla_state)
    assert np.allclose(
        estimate_agent.process_noise_covariance, estimate_agent.nominal_filter.q_matrix
    )
    assert np.allclose(estimate_agent.initial_covariance, estimate_agent._initial_covariance)
    assert np.allclose(estimate_agent.error_covariance, estimate_agent._error_covariance)
    assert estimate_agent.nominal_filter is estimate_agent._filter
    assert estimate_agent.visual_cross_section == estimate_agent._visual_cross_section
    assert estimate_agent.mass == estimate_agent._mass
    assert estimate_agent.reflectivity == estimate_agent._reflectivity


def testSetters(estimate_agent: EstimateAgent):
    """Test setters.

    Args:
        estimate_agent (:class:`.EstimateAgent`): Estimate agent fixture
    """
    bad_covariance = np.diagflat(np.ones((5, 6)))

    with pytest.raises(ShapeError):
        estimate_agent.error_covariance = bad_covariance

    new_state = np.ones(6)
    estimate_agent.state_estimate = new_state

    assert np.allclose(
        estimate_agent.ecef_state, eci2ecef(new_state, estimate_agent.datetime_epoch)
    )
