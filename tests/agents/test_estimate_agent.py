"""Test :class:`.EstimateAgent`."""

from __future__ import annotations

# Standard Library Imports
from unittest.mock import MagicMock, create_autospec, patch

# Third Party Imports
import numpy as np
import pytest

# RESONAATE Imports
import resonaate.estimation.initial_orbit_determination
from resonaate.agents.estimate_agent import EstimateAgent
from resonaate.common.exceptions import ShapeError
from resonaate.common.utilities import getTypeString
from resonaate.data.observation import Observation
from resonaate.dynamics.integration_events.station_keeping import KeepGeoEastWest
from resonaate.dynamics.two_body import TwoBody
from resonaate.estimation.adaptive.adaptive_filter import AdaptiveFilter
from resonaate.estimation.adaptive.gpb1 import GeneralizedPseudoBayesian1
from resonaate.estimation.initial_orbit_determination import IODSolution
from resonaate.estimation.kalman.unscented_kalman_filter import UnscentedKalmanFilter
from resonaate.estimation.maneuver_detection import StandardNis
from resonaate.estimation.sequential_filter import FilterFlag
from resonaate.physics.time.stardate import ScenarioTime
from resonaate.physics.transforms.methods import eci2ecef
from resonaate.scenario.clock import ScenarioClock
from resonaate.scenario.config.estimation_config import GPB1AdaptiveEstimationConfig

# pylint: disable=protected-access
pytestmark = pytest.mark.usefixtures("database")


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
            ],
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
    nominal_filter: UnscentedKalmanFilter,
    mocked_clock: ScenarioClock,
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
    nominal_filter: UnscentedKalmanFilter,
    mocked_clock: ScenarioClock,
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


@patch("resonaate.agents.agent_base.checkTypes", new=MagicMock(return_value=True))
def testEstimateAgentStationKeeping(mocked_clock: ScenarioClock):
    """Test EstimateAgent with station keeping."""
    msg = r"Estimates do not perform station keeping maneuvers"
    ukf = create_autospec(UnscentedKalmanFilter, instance=True)
    ukf.dynamics = TwoBody()
    with pytest.raises(ValueError, match=msg):
        _ = EstimateAgent(
            10001,
            "estimate_agent",
            "Spacecraft",
            mocked_clock,
            np.ones(6),
            np.ones((6, 6)),
            ukf,
            None,
            None,
            10.0,
            100.0,
            0.21,
            station_keeping=[MagicMock(spec=KeepGeoEastWest)],
        )


@patch.object(EstimateAgent, "__init__")
@patch("resonaate.agents.estimate_agent.sequentialFilterFactory")
@patch("resonaate.agents.estimate_agent.noiseCovarianceFactory")
@patch("resonaate.agents.estimate_agent.initialEstimateNoise")
def testFromConfig(
    initial_noise_func: MagicMock,
    noise_factory: MagicMock,
    filter_factory: MagicMock,
    patched_init: MagicMock,
    mocked_clock: ScenarioClock,
):
    """Test fromConfig alt constructor."""
    tgt_cfg = MagicMock()
    tgt_cfg.state.toECI = MagicMock(return_value=np.array([0, 1, 2, 3, 4, 5]))

    noise_cfg = MagicMock()
    noise_cfg.random_seed = 100000
    time_cfg = MagicMock()
    dynamics = MagicMock()
    est_cfg = MagicMock()

    initial_noise_func.return_value = (np.array([1, 2, 3, 4, 5, 6]), np.eye(6))
    noise_factory.return_value = np.eye(6)

    # Required to ensure the call works
    patched_init.return_value = None

    EstimateAgent.fromConfig(tgt_cfg, mocked_clock, dynamics, time_cfg, noise_cfg, est_cfg)

    initial_noise_func.assert_called_once()
    noise_factory.assert_called_once()
    filter_factory.assert_called_once()
    patched_init.assert_called_once()


def testUpdateNoObservations(estimate_agent: EstimateAgent, observations: Observation):
    """Test update without observations.

    Args:
        estimate_agent (:class:`.EstimateAgent`): Estimate agent fixture
        observations (:class:`.Observation`): Observation tuple fixture
    """
    estimate_agent.nominal_filter.predict(ScenarioTime(60.0))
    estimate_agent.nominal_filter.forecast(observations)
    estimate_agent.update([])

    assert np.allclose(estimate_agent.state_estimate, estimate_agent.nominal_filter.est_x)
    assert np.allclose(estimate_agent.error_covariance, estimate_agent.nominal_filter.est_p)


def testUpdateWithObservations(estimate_agent: EstimateAgent, observations: Observation):
    """Test update without observations.

    Args:
        estimate_agent (:class:`.EstimateAgent`): Estimate agent fixture
        observations (:class:`.Observation`): Observation tuple fixture
    """
    estimate_agent.nominal_filter.predict(ScenarioTime(60.0))
    estimate_agent.nominal_filter.forecast(observations)
    estimate_agent.update(observations)

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


def testHandleDetectedManeuver(estimate_agent: EstimateAgent, observations: Observation):
    """Test _handleManeuverDetection.

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
    estimate_agent._handleManeuverDetection(observations)
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
    estimate_agent._handleManeuverDetection(observations)
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
    estimate_agent.update(observations)

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
    estimate_agent.update(observations)

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
    estimate_agent.nominal_filter.checkManeuverDetection = MagicMock()

    # Update with a maneuver detection
    estimate_agent.update(observations)
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
    estimate_agent.nominal_filter.maneuver_detected = True

    # Update with a maneuver detection
    estimate_agent.update(observations)
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
    iod_estimate_agent.nominal_filter.update(observations)
    iod_estimate_agent.nominal_filter.maneuver_detected = True

    # Patch IOD logic
    def mockIOD(self, observations):
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
        adaptive_filter_config=GPB1AdaptiveEstimationConfig(
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
        adaptive_filter_config=GPB1AdaptiveEstimationConfig(
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


def testHandleIODReturn(estimate_agent: EstimateAgent, observations: list[Observation]):
    """Test _handleIOD returns if no IOD set.

    Args:
        estimate_agent (:class:`.EstimateAgent`): Estimate agent fixture
        observations: Observations fixture
    """
    estimate_agent._handleIOD(observations)

    assert estimate_agent.iod_start_time is None


def testHandleIODContinue(iod_estimate_agent: EstimateAgent, observations: list[Observation]):
    """Test _handleIOD sets iod start time.

    Args:
        iod_estimate_agent (:class:`.EstimateAgent`): Estimate agent fixture with IOD on.
        observations: Observations fixture
    """
    iod_estimate_agent.nominal_filter.maneuver_detected = False
    iod_estimate_agent._handleIOD(observations)

    assert iod_estimate_agent.iod_start_time is None


def testHandleIODSuccess(iod_estimate_agent: EstimateAgent, observations: list[Observation]):
    """Test _handleIOD sets iod start time.

    Args:
        iod_estimate_agent (:class:`.EstimateAgent`): Estimate agent fixture with IOD on.
        observations: Observations fixture
    """
    iod_estimate_agent._handleManeuverDetection(observations)
    iod_estimate_agent._handleIOD(observations)

    assert iod_estimate_agent.iod_start_time == iod_estimate_agent.time


def testHandleIODNoSuccess(iod_estimate_agent: EstimateAgent, observations: list[Observation]):
    """Test _handleIOD sets iod start time.

    Args:
        iod_estimate_agent (:class:`.EstimateAgent`): Estimate agent fixture with IOD on.
        observations (:class:`.Observation`): Observation tuple fixture
    """
    iod_estimate_agent.nominal_filter.predict(ScenarioTime(60.0))
    iod_estimate_agent.nominal_filter.update(observations)
    iod_estimate_agent._update(observations=observations)

    assert iod_estimate_agent.iod_start_time == iod_estimate_agent.time


def testNoAttemptInitialOrbitDetermination(
    estimate_agent: EstimateAgent,
    observations: list[Observation],
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
    observations: list[Observation],
):
    """Test _attemptInitialOrbitDetermination with no success.

    Args:
        iod_estimate_agent (:class:`.EstimateAgent`): Estimate agent fixture with IOD on.
        observations (:class:`.Observation`): Observation tuple fixture
    """
    iod_estimate_agent._handleManeuverDetection(observations)
    iod_estimate_agent._handleIOD(observations)
    assert iod_estimate_agent.iod_start_time == ScenarioTime(0.0)

    # Test unsuccessful IOD
    iod_estimate_agent.time = ScenarioTime(300.0)
    fail, iod_state = iod_estimate_agent._attemptInitialOrbitDetermination(observations)

    assert fail is False
    assert iod_state is None


def testAttemptInitialOrbitDeterminationBadTime(
    iod_estimate_agent: EstimateAgent,
    observations: list[Observation],
):
    """Test _attemptInitialOrbitDetermination with a bad IOD start time.

    Args:
        iod_estimate_agent (:class:`.EstimateAgent`): Estimate agent fixture with IOD on.
        observations (:class:`.Observation`): Observation tuple fixture
    """
    iod_estimate_agent._handleManeuverDetection(observations)
    iod_estimate_agent._handleIOD(observations)
    assert iod_estimate_agent.iod_start_time == ScenarioTime(0.0)

    # Test unsuccessful IOD
    iod_estimate_agent.iod_start_time = ScenarioTime(3000.0)
    msg = r"IOD .*: ScenarioTime\(\d*.\d* seconds\) .*: ScenarioTime\(\d*.\d* seconds\)"
    with pytest.raises(ValueError, match=msg):
        _, _ = iod_estimate_agent._attemptInitialOrbitDetermination(observations)


def testAttemptInitialOrbitDeterminationSuccess(
    iod_estimate_agent: EstimateAgent,
    observations: list[Observation],
    monkeypatch: pytest.MonkeyPatch,
):
    """Test _attemptInitialOrbitDetermination with success.

    Args:
        iod_estimate_agent (:class:`.EstimateAgent`): Estimate agent fixture with IOD on.
        observations (:class:`.Observation`): Observation tuple fixture
        monkeypatch (``:class:`.MonkeyPatch``): patch of function
    """
    iod_estimate_agent._handleManeuverDetection(observations)
    iod_estimate_agent._handleIOD(observations)
    assert iod_estimate_agent.iod_start_time == ScenarioTime(0.0)

    iod_estimate_agent.time = ScenarioTime(300.0)

    # Patch IOD logic
    def determineNewEstimateStateGood(self, observations, detection_time, current_time):
        return IODSolution(
            state_vector=iod_estimate_agent.state_estimate,
            convergence=True,
            message=None,
        )

    monkeypatch.setattr(
        resonaate.estimation.initial_orbit_determination.LambertIOD,
        "determineNewEstimateState",
        determineNewEstimateStateGood,
    )
    success, iod_state = iod_estimate_agent._attemptInitialOrbitDetermination(observations)

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
        estimate_agent.process_noise_covariance,
        estimate_agent.nominal_filter.q_matrix,
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
        estimate_agent.ecef_state,
        eci2ecef(new_state, estimate_agent.datetime_epoch),
    )
