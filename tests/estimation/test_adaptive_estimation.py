from __future__ import annotations

# Standard Library Imports
from typing import TYPE_CHECKING
from unittest.mock import create_autospec

# Third Party Imports
import pytest
from numpy import array, diagflat, ones, zeros

# RESONAATE Imports
import resonaate.data.resonaate_database
import resonaate.estimation.adaptive.adaptive_filter
from resonaate.agents.sensing_agent import SensingAgent
from resonaate.agents.target_agent import TargetAgent
from resonaate.common.labels import SensorLabel
from resonaate.data.ephemeris import EstimateEphemeris
from resonaate.data.observation import Observation
from resonaate.dynamics.two_body import TwoBody
from resonaate.estimation.adaptive.adaptive_filter import AdaptiveFilter
from resonaate.estimation.adaptive.gpb1 import GeneralizedPseudoBayesian1
from resonaate.estimation.adaptive.initialization import lambertInitializationFactory
from resonaate.estimation.adaptive.mmae_stacking_utils import stackingFactory
from resonaate.estimation.adaptive.smm import StaticMultipleModel
from resonaate.estimation.kalman.unscented_kalman_filter import UnscentedKalmanFilter
from resonaate.estimation.maneuver_detection import StandardNis
from resonaate.physics.time.stardate import JulianDate
from resonaate.scenario.config import constructFromUnion
from resonaate.scenario.config.estimation_config import AdaptiveEstimationConfig
from resonaate.sensors.advanced_radar import AdvRadar

# Type Checking Imports
if TYPE_CHECKING:
    # RESONAATE Imports
    from resonaate.sensors.sensor_base import Sensor


EST_X = array([6378.0, 2.0, 10.0, 0.0, 7.0, 0.0])
EST_P = diagflat([1.0, 2.0, 1.0, 1, 1, 1])
NOMINAL_FILTER = UnscentedKalmanFilter(
    10001,
    0.0,
    EST_X,
    EST_P,
    TwoBody(),
    3 * EST_P,
    StandardNis(0.01),
    None,
    False,
)
TIMESTEP = 300
ORBIT_DETERMINATION = lambertInitializationFactory("lambert_universal")
STACKING_METHOD = stackingFactory("eci_stack")
Y_DIM = 4
HYPOTHESIS_STATES = array(
    [
        [
            1.04213762e03,
            1.03337376e03,
            6.70563235e03,
            7.45441558e00,
            9.16569904e-01,
            -1.29593066e00,
        ],
        [
            1.04213762e03,
            1.03337376e03,
            6.70563235e03,
            7.45441558e00,
            9.16569904e-01,
            -1.29593066e00,
        ],
        [
            4.96882662e03,
            1.32276258e03,
            4.55146966e03,
            5.14772605e00,
            1.23195891e-02,
            -5.61649491e00,
        ],
    ],
)
JULIAN_DATE_START = JulianDate(2459304.16666666665)
PRIOR_OB_JULIAN_DATE = JulianDate(2459304.208333333)
CURRENT_JULIAN_DATE = JulianDate(2459304.270833333)
ECI1 = [
    1042.1334518641331,
    1033.37035125107,
    6705.6390684495655,
    7.454413970030313,
    0.916571711200926,
    -1.295920318595538,
]
EST1 = EstimateEphemeris().fromCovarianceMatrix(
    julian_date=PRIOR_OB_JULIAN_DATE,
    agent_id=10001,
    source="Observation",
    covariance=zeros((6, 6)),
    eci=ECI1,
)
ECI2 = [
    4968.8239260303235,
    1322.7615874648438,
    4551.484250143907,
    5.147734141833226,
    0.01232578268747098,
    -5.616480078640512,
]
EST2 = EstimateEphemeris().fromCovarianceMatrix(
    julian_date=JulianDate(2459304.2152777775),
    agent_id=10001,
    source="Observation",
    covariance=zeros((6, 6)),
    eci=ECI2,
)
ECI3 = [
    -4892.577225112445,
    -80.91957368584583,
    4811.58136651487,
    5.233352626773319,
    1.4657863428724,
    5.34613961104949,
]
EST3 = EstimateEphemeris().fromCovarianceMatrix(
    julian_date=JulianDate(2459304.2638888885),
    agent_id=10001,
    source="Observation",
    covariance=zeros((6, 6)),
    eci=ECI3,
)
MANEUVER_TIMES = array([3600, 3600, 4200, 8400])


@pytest.fixture(name="adaptive_filter")
def getTestAdaptiveFilter() -> AdaptiveFilter:
    """Create a custom :class:`AdaptiveFilter` object."""
    adaptive_filter = AdaptiveFilter(
        NOMINAL_FILTER,
        TIMESTEP,
        ORBIT_DETERMINATION,
        STACKING_METHOD,
        1,
        300,
        1e-10,
        0.997,
    )
    adaptive_filter.x_dim = 6
    adaptive_filter.pred_x = EST_X
    adaptive_filter.pred_p = diagflat(ones(adaptive_filter.x_dim))
    adaptive_filter.time = 0
    adaptive_filter.is_angular = True
    adaptive_filter.source = "Observation"
    adaptive_filter.est_x = EST_X
    adaptive_filter.est_p = diagflat(ones(adaptive_filter.x_dim))
    adaptive_filter.true_y = array([0, 1])
    adaptive_filter.mean_pred_y = array([0, 1])
    adaptive_filter.cross_cvr = ones((adaptive_filter.x_dim, Y_DIM))
    adaptive_filter.innov_cvr = ones((Y_DIM, Y_DIM))
    adaptive_filter.kalman_gain = ones((adaptive_filter.x_dim, Y_DIM))
    return adaptive_filter


@pytest.fixture(name="rso_agent")
def getTestRSOAgent() -> TargetAgent:
    """Create a custom :class:`TargetAgent` object for an RSO."""
    rso_agent = create_autospec(TargetAgent, instance=True)
    rso_agent.unique_id = 10001
    rso_agent.name = "Test_sat"
    rso_agent.eci_state = array(
        [-948.311943, 750.624874, 6767.19073, 7.46101124, 1.20802706, 0.911776855],
    )
    return rso_agent


@pytest.fixture(name="sensor_agent")
def getTestSensorAgent(earth_sensor: Sensor) -> SensingAgent:
    """Create a custom :class:`SensingAgent` object for a sensor."""
    sensor_agent = create_autospec(SensingAgent, instance=True)
    sensor_agent.unique_id = 100001
    sensor_agent.name = "Test_sensor"
    sensor_agent.eci_state = array(
        [
            -1.55267475e03,
            1.47362430e03,
            5.98812597e03,
            -1.07453539e-01,
            -1.14109571e-01,
            2.19474290e-04,
        ],
    )
    sensor_agent.ecef_state = array(
        [
            1.83995228e03,
            1.11114727e03,
            5.98497681e03,
            1.16467265e-24,
            -6.00704788e-24,
            3.01869766e-18,
        ],
    )
    sensor_agent.julian_date_epoch = JULIAN_DATE_START
    sensor_agent.lla_state = array([1.22813479, 0.54328225, 0.063])
    sensor_agent.time = 300
    sensor_agent.simulation_id = 100001

    sensor_agent.sensors = earth_sensor
    sensor_agent.sensors.host = sensor_agent
    return sensor_agent


@pytest.fixture(name="earth_sensor")
def getTestEarthSensor() -> AdvRadar:
    """Create a custom :class:`Sensor` object for a sensor."""
    return AdvRadar(
        az_mask=array([0.0, 359.99999]),
        el_mask=array([1.0, 89.0]),
        r_matrix=diagflat([2.38820057e-11, 3.73156339e-11, 9.00000000e-08, 3.61000000e-10]),
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


@pytest.fixture(name="radar_observation")
def getTestRadarObservation(sensor_agent: SensingAgent, rso_agent: TargetAgent) -> Observation:
    """Create a custom :class:`Observation` object for a sensor."""
    julian_date = JulianDate(2459304.270833333)
    return Observation(
        julian_date=julian_date,
        sensor_id=sensor_agent.unique_id,
        target_id=rso_agent.unique_id,
        sensor_type=SensorLabel.ADV_RADAR,
        azimuth_rad=0.0960304210103737,
        elevation_rad=0.3522603731619839,
        range_km=1224.6425779127965,
        range_rate_km_p_sec=3.5594024876519974,
        sensor_eci=sensor_agent.eci_state,
        measurement=sensor_agent.sensors.measurement,
    )


@pytest.fixture(name="optical_observation")
def getTestOpticalObservation(sensor_agent: SensingAgent, rso_agent: TargetAgent) -> Observation:
    """Create a custom :class:`Observation` object for a sensor."""
    julian_date = JulianDate(2459304.270833333)
    return Observation(
        julian_date=julian_date,
        sensor_id=sensor_agent.unique_id,
        target_id=rso_agent.unique_id,
        sensor_type=SensorLabel.OPTICAL,
        azimuth_rad=0.0960304210103737,
        elevation_rad=0.3522603731619839,
        sensor_eci=sensor_agent.eci_state,
        measurement=sensor_agent.sensors.measurement,
    )


class TestAdaptiveEstimation:
    """Unit test adaptive estimation base class."""

    def testInit(self):
        """Test creation of :class:`.AdaptiveEstimation`."""
        _ = AdaptiveFilter(
            NOMINAL_FILTER,
            TIMESTEP,
            ORBIT_DETERMINATION,
            STACKING_METHOD,
            1,
            300,
            1e-10,
            0.997,
        )

    def testFromConfig(self):
        """Test creation of :class:`.AdaptiveEstimation` from a config."""
        mmae_config = {
            "name": "gpb1",
            "orbit_determination": "lambert_universal",
            "model_interval": 60,
            "stacking_method": "eci_stack",
            "observation_window": 1,
            "prune_threshold": 1e-10,
            "prune_percentage": 0.997,
            "parameters": {},
        }
        config = constructFromUnion(AdaptiveEstimationConfig, mmae_config)
        _ = AdaptiveFilter.fromConfig(config, NOMINAL_FILTER, TIMESTEP)

    def testInitialize(
        self,
        monkeypatch: pytest.MonkeyPatch,
        adaptive_filter: AdaptiveFilter,
        radar_observation: Observation,
    ):
        """Test initialization of adaptive estimation & various conditions."""
        estimate_ephem = [EST1, EST2, EST3]
        radar_observation.julian_date = CURRENT_JULIAN_DATE
        obs_ephem = [radar_observation]

        def mockDb(*args, **kwargs):
            return None

        monkeypatch.setattr(
            resonaate.estimation.adaptive.adaptive_filter,
            "getDBConnection",
            mockDb,
        )

        # Creating Monkey Patch of database calls
        def mockGetEst(*args, **kwargs):
            return estimate_ephem

        monkeypatch.setattr(
            resonaate.estimation.adaptive.adaptive_filter,
            "fetchEstimatesByJDInterval",
            mockGetEst,
        )

        def mockObsBad(*args, **kwargs):
            return []

        monkeypatch.setattr(
            resonaate.estimation.adaptive.adaptive_filter,
            "fetchObservationsByJDInterval",
            mockObsBad,
        )

        bad_init_obs = adaptive_filter.initialize([radar_observation], JULIAN_DATE_START)
        assert bad_init_obs is False

        def mockObsGood(*args, **kwargs):
            return obs_ephem

        monkeypatch.setattr(
            resonaate.estimation.adaptive.adaptive_filter,
            "fetchObservationsByJDInterval",
            mockObsGood,
        )
        bad_init_models = adaptive_filter.initialize([radar_observation], JULIAN_DATE_START)
        assert bad_init_models is False

        adaptive_filter.previous_obs_window = 3
        bad_init_obs_window = adaptive_filter.initialize([radar_observation], JULIAN_DATE_START)
        assert bad_init_obs_window is False

        adaptive_filter.previous_obs_window = 1
        adaptive_filter.time = 9300
        good_init = adaptive_filter.initialize([radar_observation], JULIAN_DATE_START)
        assert good_init is True

    def testCalcNominalStates(
        self,
        monkeypatch: pytest.MonkeyPatch,
        adaptive_filter: AdaptiveFilter,
    ):
        """Test calculation of nominal states for hypotheses."""
        adaptive_filter.num_models = 3
        estimate_ephem = [EST1, EST2, EST3]

        # Creating Monkey Patch of database call
        def mockGet(*args, **kwargs):
            return estimate_ephem

        monkeypatch.setattr(
            resonaate.estimation.adaptive.adaptive_filter,
            "fetchEstimatesByJDInterval",
            mockGet,
        )

        nominal_states = adaptive_filter._calculateNominalStates(
            database=None,
            initial_jd=JULIAN_DATE_START,
            prior_obs_jd=PRIOR_OB_JULIAN_DATE,
            current_jd=CURRENT_JULIAN_DATE,
            maneuver_times=MANEUVER_TIMES,
        )
        assert nominal_states.shape == (3, 6)

    def testGenerateHypothesisStates(self, adaptive_filter: AdaptiveFilter):
        """Test generation of hypothesis states."""
        maneuvers = array(
            [
                [0.0, 0.0, 0.0],
                [-0.00669838, -0.00723921, -0.04762473],
                [-0.01061822, -10.00306015, -0.01149563],
            ],
        )
        adaptive_filter.mmae_antecedent_time = 4200
        hypothesis_states = adaptive_filter._generateHypothesisStates(
            HYPOTHESIS_STATES,
            maneuvers,
            MANEUVER_TIMES,
        )
        assert hypothesis_states.shape == (2, 6)

    def testCalcTimestep(self, adaptive_filter: AdaptiveFilter):
        """Test determining of estimation timestep."""
        adaptive_filter.model_interval = 400
        adaptive_filter.time = 600

        # Check if model_interval > scenario_time_step
        prior_ob_scenario_time = 300
        time_step, num_models = adaptive_filter._calculateTimestep(prior_ob_scenario_time)
        assert time_step == prior_ob_scenario_time
        assert num_models == 2

        # Check if model_interval < scenario_time_step
        adaptive_filter.model_interval = 60
        time_step, num_models = adaptive_filter._calculateTimestep(prior_ob_scenario_time)
        assert time_step == adaptive_filter.model_interval
        assert num_models == 6

    def testGenerateHypothesisManeuvers(
        self,
        adaptive_filter: AdaptiveFilter,
        radar_observation: Observation,
        optical_observation: Observation,
    ):
        """Test generating maneuver hypotheses."""
        adaptive_filter.num_models = 3
        adaptive_filter.est_x = array(
            [-948.311943, 750.624874, 6767.19073, 7.46101124, 1.20802706, 0.911776855],
        )
        adaptive_filter.time = 9000
        delta_v = adaptive_filter._generateHypothesisManeuvers(
            [radar_observation],
            HYPOTHESIS_STATES,
            MANEUVER_TIMES,
        )
        assert delta_v.shape == (3, 3)
        # Test Optical option
        optical_v = adaptive_filter._generateHypothesisManeuvers(
            [optical_observation],
            HYPOTHESIS_STATES,
            MANEUVER_TIMES,
        )
        assert optical_v.shape == (3, 3)

    def testInitialPruning(self, adaptive_filter: AdaptiveFilter):
        """Test initial pruning of hypotheses."""
        maneuvers = array(
            [
                [0.0, 0.0, 0.0],
                [-0.00669838, -0.00723921, -0.04762473],
                [-0.01061822, -10.00306015, -0.01149563],
            ],
        )
        crashed_indices = [2]
        hypothesis_states = adaptive_filter._initialPruning(
            maneuvers,
            crashed_indices,
            HYPOTHESIS_STATES,
        )
        assert hypothesis_states.shape == (2, 6)
        crashed_indices = [0, 1]
        hypothesis_states = adaptive_filter._initialPruning(
            maneuvers,
            crashed_indices,
            HYPOTHESIS_STATES,
        )
        assert hypothesis_states.size == 0
        assert adaptive_filter.num_models == 0

    def testCreateModels(self, adaptive_filter: AdaptiveFilter):
        """Test creating multiple models."""
        models = adaptive_filter._createModels(HYPOTHESIS_STATES)
        assert len(models) == len(HYPOTHESIS_STATES)

    def testPredict(self, adaptive_filter: AdaptiveFilter):
        """Test Adaptive Filter Predict Test."""
        adaptive_filter.models = adaptive_filter._createModels(HYPOTHESIS_STATES)
        new_time = 600
        adaptive_filter.model_weights = [1 / 3, 1 / 3, 1 / 3]
        adaptive_filter.predict(new_time)

        assert adaptive_filter.time == new_time

    def testForecast(self, adaptive_filter: AdaptiveFilter, radar_observation: Observation):
        """Test Adaptive Filter Predict Test."""
        adaptive_filter.models = adaptive_filter._createModels(HYPOTHESIS_STATES)
        new_time = 600
        adaptive_filter.model_weights = [1 / 3, 1 / 3, 1 / 3]
        adaptive_filter.predict(new_time)
        adaptive_filter.forecast([radar_observation])
        adaptive_filter._compileForecastStep([radar_observation])

    def testUpdate(self, adaptive_filter: AdaptiveFilter, radar_observation: Observation):
        """Test Adaptive Filter Predict Test."""
        adaptive_filter.models = adaptive_filter._createModels(HYPOTHESIS_STATES)
        new_time = 600
        adaptive_filter.model_weights = [1 / 3, 1 / 3, 1 / 3]
        adaptive_filter.predict(new_time)
        # Test Measurement Update
        adaptive_filter.update([radar_observation])
        # Test Propagation Update
        adaptive_filter.update([])

    def testCompilePredict(self, adaptive_filter: AdaptiveFilter):
        """Test compiling prediction step attributes."""
        adaptive_filter.models = adaptive_filter._createModels(HYPOTHESIS_STATES)
        for model in adaptive_filter.models:
            model.pred_x = zeros(6)
            model.pred_p = zeros((6, 6))
        adaptive_filter.model_weights = [1, 2, 3]
        adaptive_filter._compilePredictStep()

    def testCompileUpdate(self, adaptive_filter: AdaptiveFilter, radar_observation: Observation):
        """Test compiling update step attributes."""
        adaptive_filter.models = adaptive_filter._createModels(HYPOTHESIS_STATES)
        for model in adaptive_filter.models:
            model.pred_x = EST_X
            model.pred_p = EST_P
            model.time = 0
            model.is_angular = array([2, 3, 1, 1])
            model.source = "Observation"
            model.est_x = EST_X
            model.est_p = EST_P
            model.true_y = array([0, 1, 2, 4])
            model.mean_pred_y = array([0, 1, 3, 4])
            model.r_matrix = diagflat([1, 2, 3, 4])
            model.innovation = zeros((4, 4))
            model.nis = 1
            model.cross_cvr = ones((adaptive_filter.x_dim, Y_DIM))
            model.innov_cvr = ones((Y_DIM, Y_DIM))
            model.kalman_gain = ones((adaptive_filter.x_dim, Y_DIM))

        adaptive_filter.model_weights = ones(3) / 1
        adaptive_filter._compileUpdateStep([radar_observation])

    def testPruning(self, adaptive_filter: AdaptiveFilter):
        """Test pruning hypotheses."""
        adaptive_filter.models = adaptive_filter._createModels(HYPOTHESIS_STATES)
        adaptive_filter.num_models = 3
        adaptive_filter.model_weights = [1, 2, 3]
        adaptive_filter.model_likelihoods = [1, 2, 3]
        adaptive_filter.mode_probabilities = [0.999, 0.001, 0.001]
        adaptive_filter.models[0].pred_x = EST_X
        adaptive_filter.models[0].pred_p = EST_P
        adaptive_filter.models[0].time = 0
        adaptive_filter.models[0].is_angular = array([2, 3, 1, 1])
        adaptive_filter.models[0].source = "Observation"
        adaptive_filter.models[0].est_x = EST_X
        adaptive_filter.models[0].est_p = EST_P
        adaptive_filter.models[0].true_y = array([0, 1, 2, 4])
        adaptive_filter.models[0].mean_pred_y = array([0, 1, 3, 4])
        adaptive_filter.models[0].r_matrix = diagflat([1, 2, 3, 4])
        adaptive_filter.models[0].innovation = zeros((4, 4))
        adaptive_filter.models[0].nis = 1
        adaptive_filter.models[0].cross_cvr = ones((adaptive_filter.x_dim, Y_DIM))
        adaptive_filter.models[0].innov_cvr = ones((Y_DIM, Y_DIM))
        adaptive_filter.models[0].kalman_gain = ones((adaptive_filter.x_dim, Y_DIM))
        prune_index = array([1, 2])
        # Test pruning off model 1
        adaptive_filter.prune(prune_index, [])
        assert adaptive_filter.num_models == 1
        assert adaptive_filter.mode_probabilities[0] == 0.999
        # Test that it is impossible to prune to zero models
        adaptive_filter.prune(prune_index, [])
        assert adaptive_filter.num_models == 1

    def testCalculatingDeltaV(self, adaptive_filter: AdaptiveFilter):
        """Test calculating maneuvers for hypotheses."""
        tgt_eci_position = array([-948.311943, 750.624874, 6767.19073])
        adaptive_filter.num_models = 4
        adaptive_filter.time = 9000
        maneuvers = adaptive_filter._calculateDeltaV(
            HYPOTHESIS_STATES,
            MANEUVER_TIMES,
            tgt_eci_position,
        )
        assert maneuvers.shape == (4, 3)

    def testGetPredictionResults(self, adaptive_filter: AdaptiveFilter):
        """Test getting prediction results."""
        adaptive_filter.models = adaptive_filter._createModels(HYPOTHESIS_STATES)
        result = adaptive_filter.getPredictionResult()
        assert len(result.models) == 3

    def testGetForecastResults(self, adaptive_filter: AdaptiveFilter):
        """Test getting forecast results."""
        adaptive_filter.models = adaptive_filter._createModels(HYPOTHESIS_STATES)
        result = adaptive_filter.getForecastResult()
        assert len(result.models) == 3

    def testGetUpdateResults(self, adaptive_filter: AdaptiveFilter):
        """Test getting update results."""
        adaptive_filter.models = adaptive_filter._createModels(HYPOTHESIS_STATES)
        result = adaptive_filter.getUpdateResult()
        assert len(result.true_y) == 2

    def testResumeSequentialFiltering(self, adaptive_filter: AdaptiveFilter):
        """Test re-initializing nominal filter after MMAE ends."""
        adaptive_filter._resumeSequentialFiltering()
        assert adaptive_filter.converged_filter is not None


@pytest.fixture(name="smm")
def getTestSMM() -> StaticMultipleModel:
    """Create a custom :class:`StaticMultipleModel` object."""
    smm = StaticMultipleModel(
        NOMINAL_FILTER,
        TIMESTEP,
        ORBIT_DETERMINATION,
        STACKING_METHOD,
        1,
        300,
        1e-10,
        0.997,
    )
    smm.x_dim = 6
    smm.models = smm._createModels(HYPOTHESIS_STATES)
    smm.num_models = 3
    smm.model_weights = array([3, 1, 1])
    smm.model_likelihoods = array([1, 2, 3])
    smm.mode_probabilities = array([0.999, 0.001, 0.001])
    smm.models[0].pred_x = EST_X
    smm.models[0].pred_p = EST_P
    smm.models[0].time = 0
    smm.models[0].is_angular = array([2, 3, 1, 1])
    smm.models[0].source = "Observation"
    smm.models[0].est_x = EST_X
    smm.models[0].est_p = EST_P
    smm.models[0].true_y = array([0, 1, 2, 4])
    smm.models[0].mean_pred_y = array([0, 1, 3, 4])
    smm.models[0].r_matrix = diagflat([1, 2, 3, 4])
    smm.models[0].innovation = zeros((4, 4))
    smm.models[0].nis = 1
    smm.models[0].cross_cvr = ones((smm.x_dim, Y_DIM))
    smm.models[0].innov_cvr = ones((Y_DIM, Y_DIM))
    smm.models[0].kalman_gain = ones((smm.x_dim, Y_DIM))
    return smm


class TestSMM:
    """Unit test static multiple model class."""

    def testInitialize(
        self,
        monkeypatch: pytest.MonkeyPatch,
        radar_observation: Observation,
        smm: StaticMultipleModel,
    ):
        """Test custom initialization process."""
        estimate_ephem = [EST1, EST2, EST3]
        radar_observation.julian_date = CURRENT_JULIAN_DATE
        obs_ephem = [radar_observation]

        def mockDb(*args, **kwargs):
            return None

        monkeypatch.setattr(
            resonaate.estimation.adaptive.adaptive_filter,
            "getDBConnection",
            mockDb,
        )

        # Creating Monkey Patch of database calls
        def mockGetEst(*args, **kwargs):
            return estimate_ephem

        monkeypatch.setattr(
            resonaate.estimation.adaptive.adaptive_filter,
            "fetchEstimatesByJDInterval",
            mockGetEst,
        )

        def mockObsGood(*args, **kwargs):
            return obs_ephem

        monkeypatch.setattr(
            resonaate.estimation.adaptive.adaptive_filter,
            "fetchObservationsByJDInterval",
            mockObsGood,
        )

        smm.previous_obs_window = 1
        smm.time = 9300
        good_init = smm.initialize([radar_observation], JULIAN_DATE_START)
        assert good_init is True

    def testUpdate(self, radar_observation: Observation, smm: StaticMultipleModel):
        """Test custom update process."""
        smm.models = smm._createModels(HYPOTHESIS_STATES)
        new_time = 600
        smm.model_weights = array([1 / 3, 1 / 3, 1 / 3])
        smm.model_likelihoods = array([1, 2, 3])
        smm.predict(new_time)
        # Test Measurement Update
        smm.update([radar_observation])

    def testPruneToSingleModel(self, smm: StaticMultipleModel):
        """Test pruning to single model."""
        no_prune = smm._prunedToSingleModel([])
        assert no_prune is False
        smm.prune_threshold = 2.0
        single_model = smm._prunedToSingleModel([])
        assert single_model is True

    def testConvergedToSingleModel(
        self,
        monkeypatch: pytest.MonkeyPatch,
        smm: StaticMultipleModel,
    ):
        """Test converging to a single model."""
        no_converge = smm._convergedToSingleModel([])
        assert no_converge is False
        smm.prune_threshold = 2.0
        smm.prune_percentage = 2.0

        def mockChi2(*args, **kwargs):
            return True

        monkeypatch.setattr(resonaate.estimation.adaptive.smm, "oneSidedChiSquareTest", mockChi2)

        converge = smm._convergedToSingleModel([])
        assert converge is True

    def testPreWeight(self, smm: StaticMultipleModel, radar_observation: Observation):
        """Test pre weighting of SMM."""
        smm.models = smm._createModels(HYPOTHESIS_STATES)
        for model in smm.models:
            model.pred_x = EST_X
        smm._preWeight([radar_observation])


@pytest.fixture(name="gpb1")
def getTestGPB1() -> GeneralizedPseudoBayesian1:
    """Create a custom :class:`GeneralizedPseudoBayesian1` object."""
    gpb1 = GeneralizedPseudoBayesian1(
        NOMINAL_FILTER,
        TIMESTEP,
        ORBIT_DETERMINATION,
        STACKING_METHOD,
        1,
        300,
        1e-10,
        0.997,
    )
    gpb1.x_dim = 6
    gpb1.models = gpb1._createModels(HYPOTHESIS_STATES)
    gpb1.num_models = 3
    gpb1.model_weights = array([3, 1, 1])
    gpb1.model_likelihoods = array([1, 2, 3])
    gpb1.mode_probabilities = array([0.999, 0.001, 0.001])
    gpb1.models[0].pred_x = EST_X
    gpb1.models[0].pred_p = EST_P
    gpb1.models[0].time = 0
    gpb1.models[0].is_angular = array([2, 3, 1, 1])
    gpb1.models[0].source = "Observation"
    gpb1.models[0].est_x = EST_X
    gpb1.models[0].est_p = EST_P
    gpb1.models[0].true_y = array([0, 1, 2, 4])
    gpb1.models[0].mean_pred_y = array([0, 1, 3, 4])
    gpb1.models[0].r_matrix = diagflat([1, 2, 3, 4])
    gpb1.models[0].innovation = zeros((4, 4))
    gpb1.models[0].nis = 1
    gpb1.models[0].cross_cvr = ones((gpb1.x_dim, Y_DIM))
    gpb1.models[0].innov_cvr = ones((Y_DIM, Y_DIM))
    gpb1.models[0].kalman_gain = ones((gpb1.x_dim, Y_DIM))
    return gpb1


class TestGPB1:
    """Unit test Gauss pseudo Bayesian first order class."""

    def testInitialize(
        self,
        monkeypatch: pytest.MonkeyPatch,
        radar_observation: Observation,
        gpb1: GeneralizedPseudoBayesian1,
    ):
        """Test custom initialization process."""
        estimate_ephem = [EST1, EST2, EST3]
        radar_observation.julian_date = CURRENT_JULIAN_DATE
        obs_ephem = [radar_observation]

        def mockDb(*args, **kwargs):
            return None

        monkeypatch.setattr(
            resonaate.estimation.adaptive.adaptive_filter,
            "getDBConnection",
            mockDb,
        )

        # Creating Monkey Patch of database calls
        def mockGetEst(*args, **kwargs):
            return estimate_ephem

        monkeypatch.setattr(
            resonaate.estimation.adaptive.adaptive_filter,
            "fetchEstimatesByJDInterval",
            mockGetEst,
        )

        def mockObsGood(*args, **kwargs):
            return obs_ephem

        monkeypatch.setattr(
            resonaate.estimation.adaptive.adaptive_filter,
            "fetchObservationsByJDInterval",
            mockObsGood,
        )

        gpb1.previous_obs_window = 1
        gpb1.time = 9300
        good_init = gpb1.initialize([radar_observation], JULIAN_DATE_START)
        assert good_init is True

    def testUpdate(self, gpb1: GeneralizedPseudoBayesian1, radar_observation: Observation):
        """Test custom update process."""
        gpb1.models = gpb1._createModels(HYPOTHESIS_STATES)
        new_time = 600
        gpb1.model_weights = array([1 / 3, 1 / 3, 1 / 3])
        gpb1.model_likelihoods = array([1, 2, 3])
        gpb1.predict(new_time)
        # Test Measurement Update
        gpb1.update([radar_observation])

    def testConstructMixMatrix(self, gpb1: GeneralizedPseudoBayesian1):
        """Test custom update process."""
        mix = gpb1._constructMixMatrix()
        tru_mix = array(
            [
                [0.42857143, 0.28571429, 0.28571429],
                [0.28571429, 0.42857143, 0.28571429],
                [0.28571429, 0.28571429, 0.42857143],
            ],
        )
        assert mix.all() == tru_mix.all()
