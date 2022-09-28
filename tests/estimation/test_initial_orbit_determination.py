"""Test initial_orbit_determination."""
# Standard Library Imports
from copy import deepcopy

# Third Party Imports
import pytest
from numpy import allclose, array, ndarray

# RESONAATE Imports
import resonaate.data.resonaate_database
import resonaate.estimation.initial_orbit_determination
from resonaate.data.observation import Observation
from resonaate.data.resonaate_database import ResonaateDatabase
from resonaate.estimation import initialOrbitDeterminationFactory
from resonaate.estimation.initial_orbit_determination import LambertIOD
from resonaate.physics.orbit_determination.lambert import lambertUniversal
from resonaate.physics.time.stardate import JulianDate
from resonaate.scenario.config.estimation_config import InitialOrbitDeterminationConfig
from resonaate.sensors.sensor_base import ObservationTuple


@pytest.fixture(name="observation_tuple")
def getObservationTuple():
    """Create a custom :class:`.ObservationTuple` object for a sensor."""
    observation = Observation.fromSEZVector(
        azimuth_rad=0.09602716376813725,
        elevation_rad=0.35224625415803246,
        range_km=1224.6424141388,
        range_rate_km_p_sec=3.5593828053095304,
        sensor_id=300000,
        target_id=10001,
        sensor_type="AdvRadar",
        julian_date=JulianDate(2459304.270833333),
        sez=[-1144.1534998427103, 110.21257500982736, 422.5099063584762],
        sensor_position=[1.228134787553298, 0.5432822498364407, 0.06300000000101136],
    )
    return ObservationTuple(observation, None, array([2, 3, 1, 1]), "Visible")


@pytest.fixture(name="observation")
def getObservation():
    """Create a custom :class:`.Observation` object for a sensor."""
    return Observation.fromSEZVector(
        julian_date=JulianDate(2459304.374333333),
        sensor_id=300000,
        target_id=10001,
        sensor_type="AdvRadar",
        azimuth_rad=1.6987392624304676,
        elevation_rad=0.11988405069764828,
        range_km=1953.389877894924,
        range_rate_km_p_sec=-6.1473412228123365,
        sez=[247.45853451777919, 1923.5170160471882, 233.61929237537493],
        sensor_position=[1.228134787553298, 0.5432822498364407, 0.06300000000101136],
    )


@pytest.fixture(name="iod")
def getIOD():
    """Create a custom :class:`.LambertIOD` object for testing."""
    return LambertIOD(60, lambertUniversal, 10001, JulianDate(2459304.270833333))


class TestLambertInitialOrbitDetermination:
    """Unit test Lambert initial orbit determination class."""

    start_julian_date = JulianDate(2459304.16666666665)
    prior_julian_date = JulianDate(2459304.208333333)
    observation_array = array(
        [
            -2633.759315270262,
            -1659.4888414259772,
            6127.246729070783,
            0.12101630117705994,
            -0.19296395220243734,
            -0.0002437824064893823,
        ]
    )

    def testIODFactory(self, iod: LambertIOD):
        """Test IOD factory method.

        Args:
            iod (:class:`.LambertIOD`): LambertIOD fixture
        """
        config = InitialOrbitDeterminationConfig()
        factory_result = initialOrbitDeterminationFactory(
            config, iod.sat_num, self.start_julian_date
        )
        assert factory_result is not None

    def testBadIODFactory(self, iod: LambertIOD):
        """Test bad inputs for Lambert IOD factory.

        Args:
            iod (:class:`.LambertIOD`): LambertIOD fixture
        """
        bad_result = initialOrbitDeterminationFactory(None, iod.sat_num, self.start_julian_date)
        assert bad_result is None

        bad_config = InitialOrbitDeterminationConfig()
        bad_config.name = "bad_name"
        with pytest.raises(
            ValueError, match=f"Invalid Initial Orbit Determination type: {bad_config.name}"
        ):
            _ = initialOrbitDeterminationFactory(bad_config, iod.sat_num, self.start_julian_date)

    def testLambertInit(self):
        """Test Lambert init function."""
        iod_init = LambertIOD(60, lambertUniversal, 10001, self.start_julian_date)
        assert iod_init.min_observations == 2
        assert iod_init.minimum_observation_spacing == 60
        assert iod_init.orbit_determination_method is lambertUniversal
        assert iod_init.sat_num == 10001
        assert iod_init.julian_date_start is self.start_julian_date

    def testFromConfig(self, iod: LambertIOD):
        """Test fromConfig function.

        Args:
            iod (:class:`.LambertIOD`): LambertIOD fixture
        """
        config = InitialOrbitDeterminationConfig()
        init = LambertIOD.fromConfig(config, iod.sat_num, iod.julian_date_start)
        assert init.min_observations == 2
        assert init.minimum_observation_spacing is iod.minimum_observation_spacing
        assert init.orbit_determination_method is lambertUniversal
        assert init.sat_num is iod.sat_num
        assert init.julian_date_start is iod.julian_date_start

    def testGetPreviousObservations(
        self, observation: Observation, monkeypatch: pytest.MonkeyPatch, iod: LambertIOD
    ):
        """Test getPreviousObservations() function.

        Args:
            observation (:class:`.Observation`): Observation fixture
            monkeypatch (``:class:`.MonkeyPatch``): patch of function
            iod (:class:`.LambertIOD`): LambertIOD fixture
        """

        def getData(self, query, multi):  # pylint:disable=unused-argument
            return observation

        monkeypatch.setattr(
            resonaate.data.resonaate_database,
            "ResonaateDatabase",
            getData,
        )
        database = ResonaateDatabase()
        result = iod.getPreviousObservations(
            database,
            self.prior_julian_date.convertToScenarioTime(self.start_julian_date),
            iod.julian_date_start.convertToScenarioTime(self.start_julian_date),
        )
        assert result == []

    def testConvertObservationToECI(self, iod: LambertIOD, observation: Observation):
        """Test convertObservationToECI() function.

        Args:
            iod (:class:`.LambertIOD): LambertIOD fixture
            observation (:class:`.Observation`): Observation fixture
        """
        result = iod.convertObservationToECI(observation)
        assert allclose(result, self.observation_array)

    def testCheckSinglePass(self, iod: LambertIOD):
        """Test checkSinglePass() function.

        Args:
            iod (:class:`.LambertIOD`): LambertIOD fixture
        """
        # Test not single pass
        result = iod.checkSinglePass(
            self.observation_array, self.prior_julian_date, iod.julian_date_start
        )
        assert result is False

        # Test single pass
        test_julian_date = JulianDate(2459304.20833334)
        result = iod.checkSinglePass(
            self.observation_array, self.prior_julian_date, test_julian_date
        )
        assert isinstance(result, float)

        # Test julian_date_2 < julian_date_1
        bad_julian_date = JulianDate(-1)
        with pytest.raises(ValueError):  # noqa: PT011
            assert iod.checkSinglePass(
                self.observation_array, self.prior_julian_date, bad_julian_date
            )

    def testDetermineNewEstimateState(
        self,
        observation: Observation,
        observation_tuple: ObservationTuple,
        caplog: pytest.CaptureFixture,
        monkeypatch: pytest.MonkeyPatch,
        iod: LambertIOD,
    ):
        """Test determineNewEstimateState() function.

        Args:
            observation (:class:`.Observation`): Observation fixture
            observation_tuple (:class:`.ObservationTuple`): ObservationTuple fixture
            caplog (:class:`.LogCaptureFixture`): pytest logging capture
            monkeypatch (``:class:`.MonkeyPatch``): patch of function
            iod (:class:`.LambertIOD`): LambertIOD fixture
        """
        # Test Early Return because no ObsTuples
        prior_scenario_time = self.prior_julian_date.convertToScenarioTime(self.start_julian_date)
        current_scenario_time = iod.julian_date_start.convertToScenarioTime(self.start_julian_date)
        result = iod.determineNewEstimateState([], prior_scenario_time, current_scenario_time)
        assert caplog.record_tuples[-1][-1] == "No ObservationTuples for IOD"

        # Monkey Patch json loads
        def mockLoads(*args, **kwargs):  # pylint:disable=unused-argument
            return None

        monkeypatch.setattr(resonaate.estimation.initial_orbit_determination, "loads", mockLoads)

        result = iod.determineNewEstimateState(
            observation_tuple, prior_scenario_time, current_scenario_time
        )

        assert caplog.record_tuples[-1][-1] == "Not enough observations to perform IOD 0"

        # Monkey Patch get previous observation
        def mockGetPreviousObservations(*args, **kwargs):  # pylint:disable=unused-argument
            return [observation]

        monkeypatch.setattr(
            resonaate.estimation.initial_orbit_determination.LambertIOD,
            "getPreviousObservations",
            mockGetPreviousObservations,
        )

        bad_obs_tuple = deepcopy(observation_tuple)
        bad_obs_tuple.observation.range_km = None
        result = iod.determineNewEstimateState(
            [bad_obs_tuple], prior_scenario_time, current_scenario_time
        )

        assert caplog.record_tuples[-1][-1] == "No Radar observations to perform Lambert IOD"

        # Monkey Patch get single pass
        def mockCheckSinglePass(*args, **kwargs):  # pylint:disable=unused-argument
            return None

        with monkeypatch.context() as m_patch:
            m_patch.setattr(
                resonaate.estimation.initial_orbit_determination.LambertIOD,
                "checkSinglePass",
                mockCheckSinglePass,
            )

            result = iod.determineNewEstimateState(
                [observation_tuple], prior_scenario_time, current_scenario_time
            )

            assert caplog.record_tuples[-1][-1] == "Observations not from a single pass"

        # Test Successful IOD

        result = iod.determineNewEstimateState(
            [observation_tuple], prior_scenario_time, current_scenario_time
        )

        assert isinstance(result[0], ndarray)
        assert result[1] is True
