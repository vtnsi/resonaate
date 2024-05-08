"""Test initial_orbit_determination."""

from __future__ import annotations

# Standard Library Imports
from copy import deepcopy
from unittest.mock import MagicMock

# Third Party Imports
import pytest
from numpy import array, eye, ndarray

# RESONAATE Imports
import resonaate.data.resonaate_database
import resonaate.estimation.initial_orbit_determination
from resonaate.common.labels import SensorLabel
from resonaate.data.observation import Observation
from resonaate.data.resonaate_database import ResonaateDatabase
from resonaate.estimation import initialOrbitDeterminationFactory
from resonaate.estimation.initial_orbit_determination import LambertIOD
from resonaate.physics.measurements import Measurement
from resonaate.physics.orbit_determination.lambert import lambertUniversal
from resonaate.physics.time.stardate import JulianDate, julianDateToDatetime
from resonaate.physics.transforms.methods import ecef2eci, lla2ecef
from resonaate.scenario.config.estimation_config import InitialOrbitDeterminationConfig


@pytest.fixture(name="observation")
def getObservation():
    """Create a custom :class:`.Observation` object for a sensor."""
    jd = JulianDate(2459304.374333333)
    utc_datetime = julianDateToDatetime(jd)
    sen_eci_state = ecef2eci(
        lla2ecef(
            [
                1.228134787553298,
                0.5432822498364407,
                0.06300000000101136,
            ],
        ),
        utc_datetime,
    )
    return Observation(
        julian_date=jd,
        sensor_id=300000,
        target_id=10001,
        sensor_type=SensorLabel.ADV_RADAR,
        azimuth_rad=1.6987392624304676,
        elevation_rad=0.11988405069764828,
        range_km=1953.389877894924,
        range_rate_km_p_sec=-6.1473412228123365,
        sensor_eci=sen_eci_state,
        measurement=Measurement.fromMeasurementLabels(
            ["azimuth_rad", "elevation_rad", "range_km", "range_rate_km_p_sec"],
            eye(4),
        ),
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
            -2633.807719527016,
            -1659.4116569532341,
            6127.246826579328,
            0.12101067280870113,
            -0.19296748190340082,
            -0.0002437709361113743,
        ],
    )

    def testIODFactory(self, iod: LambertIOD):
        """Test IOD factory method.

        Args:
            iod (:class:`.LambertIOD`): LambertIOD fixture
        """
        config = InitialOrbitDeterminationConfig()
        factory_result = initialOrbitDeterminationFactory(
            config,
            iod.sat_num,
            self.start_julian_date,
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
            ValueError,
            match=f"Invalid Initial Orbit Determination type: {bad_config.name}",
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
        self,
        observation: Observation,
        monkeypatch: pytest.MonkeyPatch,
        iod: LambertIOD,
    ):
        """Test getPreviousObservations() function.

        Args:
            observation (:class:`.Observation`): Observation fixture
            monkeypatch (``:class:`.MonkeyPatch``): patch of function
            iod (:class:`.LambertIOD`): LambertIOD fixture
        """

        def getData(self, query, multi):
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

    def testCheckSinglePass(self, iod: LambertIOD):
        """Test checkSinglePass() function.

        Args:
            iod (:class:`.LambertIOD`): LambertIOD fixture
        """
        # Test not single pass
        result = iod.checkSinglePass(
            self.observation_array,
            self.prior_julian_date,
            iod.julian_date_start,
        )
        assert result is False

        # Test single pass
        test_julian_date = JulianDate(2459304.20833334)
        result = iod.checkSinglePass(
            self.observation_array,
            self.prior_julian_date,
            test_julian_date,
        )
        assert isinstance(result, float)

        # Test julian_date_2 < julian_date_1
        bad_julian_date = JulianDate(-1)
        with pytest.raises(ValueError):  # noqa: PT011
            assert iod.checkSinglePass(
                self.observation_array,
                self.prior_julian_date,
                bad_julian_date,
            )

    def testDetermineNewEstimateState(
        self,
        observation: Observation,
        monkeypatch: pytest.MonkeyPatch,
        iod: LambertIOD,
    ):
        """Test determineNewEstimateState() function.

        Args:
            observation (:class:`.Observation`): Observation fixture
            monkeypatch (``:class:`.MonkeyPatch``): patch of function
            iod (:class:`.LambertIOD`): LambertIOD fixture
        """
        # Test Early Return because no ObsTuples
        prior_scenario_time = self.prior_julian_date.convertToScenarioTime(self.start_julian_date)
        current_scenario_time = iod.julian_date_start.convertToScenarioTime(self.start_julian_date)
        result = iod.determineNewEstimateState([], prior_scenario_time, current_scenario_time)
        assert result.message == "No Observations for IOD"

        def mockDb(*args, **kwargs):
            mocked_db = MagicMock(spec=ResonaateDatabase)
            mocked_db.getData = lambda query: []  # noqa: ARG005
            return mocked_db

        monkeypatch.setattr(
            resonaate.estimation.initial_orbit_determination,
            "getDBConnection",
            mockDb,
        )

        result = iod.determineNewEstimateState(
            observation,
            prior_scenario_time,
            current_scenario_time,
        )

        assert result.message == "No observations in database of RSO 10001"

        # Monkey Patch get previous observation
        def mockGetPreviousObservations(*args, **kwargs):
            return [observation]

        monkeypatch.setattr(
            resonaate.estimation.initial_orbit_determination.LambertIOD,
            "getPreviousObservations",
            mockGetPreviousObservations,
        )

        bad_obs = deepcopy(observation)
        bad_obs.range_km = None
        result = iod.determineNewEstimateState(
            [bad_obs],
            prior_scenario_time,
            current_scenario_time,
        )

        assert result.message == "No Radar observations to perform Lambert IOD"

        # Monkey Patch get single pass
        def mockCheckSinglePass(*args, **kwargs):
            return None

        with monkeypatch.context() as m_patch:
            m_patch.setattr(
                resonaate.estimation.initial_orbit_determination.LambertIOD,
                "checkSinglePass",
                mockCheckSinglePass,
            )

            result = iod.determineNewEstimateState(
                [observation],
                prior_scenario_time,
                current_scenario_time,
            )

            assert result.message == "Observations not from a single pass"

        # Test Successful IOD

        result = iod.determineNewEstimateState(
            [observation],
            prior_scenario_time,
            current_scenario_time,
        )

        assert isinstance(result.state_vector, ndarray)
        assert result.convergence is True
