# pylint: disable=attribute-defined-outside-init, no-self-use
# Standard Library Imports
from datetime import datetime
# Third Party Imports
import pytest
import numpy as np
from scipy.linalg import norm

# RESONAATE Imports
try:
    import resonaate.physics.transforms.methods as transforms
    from resonaate.physics.orbit import Orbit
    from resonaate.dynamics.special_perturbations import SpecialPerturbations
    import resonaate.dynamics.integration_events.station_keeping as station_keeping
    from resonaate.physics.bodies import Earth
    from resonaate.physics import constants as const
    from resonaate.physics.time.stardate import datetimeToJulianDate
    from resonaate.scenario.config.geopotential_config import GeopotentialConfig
    from resonaate.scenario.config.perturbations_config import PerturbationsConfig
    from resonaate.scenario.clock import updateReductionParameters, updateThirdBodyPositions, BODIES
except ImportError as error:
    raise Exception(
        "Please ensure you have appropriate packages installed:\n {0}".format(error)
    ) from error
# Testing Imports
from ..conftest import BaseTestCase


TEST_START_JD = datetimeToJulianDate(datetime(2018, 12, 1, 12))

GEOPOTENTIAL_CONFIG = {
    "model": "egm96.txt",
    "degree": 4,
    "order": 4
}

PERTURBATIONS_CONFIG = {
    "third_bodies": ["sun", "moon"]
}


@pytest.fixture(name="geopotential_config")
def getGeopotentialConfig():
    """Return a :class:`.GeopotentialConfig` object based on :attr:`.GEOPOTENTIAL_CONFIG`."""
    config = GeopotentialConfig()
    config.readConfig(GEOPOTENTIAL_CONFIG)
    return config


@pytest.fixture(name="perturbations_config")
def getPerturbationsConfig():
    """Return a :class:`.PerturbationsConfig` object based on :attr:`.PERTURBATIONS_CONFIG`."""
    config = PerturbationsConfig()
    config.readConfig(PERTURBATIONS_CONFIG)
    return config


@pytest.fixture(autouse=True)
def updateParams():
    """Make sure reduction parameters and third body positions are up to date."""
    updateReductionParameters(TEST_START_JD)
    updateThirdBodyPositions(TEST_START_JD, BODIES)


@pytest.fixture(name="dynamics_obj")
def getDynamics(perturbations_config, geopotential_config):
    """Return a :class:`.SpecialPerturbations` object based on configurations."""
    return SpecialPerturbations(TEST_START_JD, geopotential_config, perturbations_config)


class TestStationKeeping(BaseTestCase):
    """Collection of unit tests to validate station keeping."""

    PROPAGATE_DURATION = 15 * 60

    LEO_TEST_RSO = 41858
    LEO_TEST_ECI = np.asarray([
        7097.477298192772,
        -674.3173082329968,
        -12.92097054001591,
        -0.09546594991208918,
        -1.0905362226946338,
        7.411054899080652
    ])

    GEO_TEST_RSO = 27414
    GEO_TEST_ECI = np.asarray([
        7772.578605391435,
        41451.327150257275,
        -13.013957256406881,
        -3.0166132050756818,
        0.566000461604396,
        0.17125923555827943
    ])

    def testKeepLeoUpInit(self, ):
        """Validate that the LEO station keeper object can be correctly instantiated."""
        station_keeper = station_keeping.KeepLeoUp.fromInitECI(self.LEO_TEST_RSO, self.LEO_TEST_ECI)
        assert np.array_equal(station_keeper.initial_eci, self.LEO_TEST_ECI)
        assert station_keeper.initial_coe == Orbit.rv2coe(self.LEO_TEST_ECI)
        assert station_keeper.ntw_delta_v == 0.0

    def testKeepLeoUpInterruptNotRequired(self, ):
        """Validate that the LEO station keeper object doesn't incorrectly require interrupt."""
        station_keeper = station_keeping.KeepLeoUp.fromInitECI(self.LEO_TEST_RSO, self.LEO_TEST_ECI)
        assert station_keeper.interruptRequired(0.0, self.LEO_TEST_ECI) is False
        assert station_keeper(0.0, self.LEO_TEST_ECI) != 0

    def testKeepLeoUpInterruptRequired(self, ):
        """Validate that the LEO station keeper object correctly requires interrupt."""
        station_keeper = station_keeping.KeepLeoUp.fromInitECI(self.LEO_TEST_RSO, self.LEO_TEST_ECI)
        coe = Orbit.rv2coe(self.LEO_TEST_ECI)
        coe.semimajor_axis -= station_keeping.KeepLeoUp.ALT_DRIFT_THRESHOLD * 1.1
        coe.semilatus_rectum = coe.semimajor_axis * (1 - coe.eccentricity**2)
        coe.period = 2 * const.PI * np.sqrt(coe.semimajor_axis**3 / Earth.mu)
        new_state = coe.coe2rv()
        assert station_keeper.interruptRequired(0.0, new_state) is True
        assert station_keeper(0.0, new_state) == 0

    def testKeepLeoUpPropagation(self, dynamics_obj):
        """Validate that the LEO station keeping maneuver executes when it's supposed to."""
        station_keeper = station_keeping.KeepLeoUp.fromInitECI(self.LEO_TEST_RSO, self.LEO_TEST_ECI)
        dynamics_obj.propagate(0.0, self.PROPAGATE_DURATION, self.LEO_TEST_ECI, station_keeping=[station_keeper])
        assert station_keeper.getActivationDetails() != (None, None)

    def testGeoEastWestInit(self, ):
        """Validate that the GEO East-West station keeper object can be correctly instantiated."""
        station_keeper = station_keeping.KeepGeoEastWest.fromInitECI(self.GEO_TEST_RSO, self.GEO_TEST_ECI)
        assert np.array_equal(station_keeper.initial_eci, self.GEO_TEST_ECI)
        assert station_keeper.initial_coe == Orbit.rv2coe(self.GEO_TEST_ECI)
        assert station_keeper.ntw_delta_v == 0.0

    def testGeoEastWestInterruptNotRequired(self, ):
        """Validate that the GEO East-West station keeper object doesn't incorrectly require interrupt."""
        station_keeper = station_keeping.KeepGeoEastWest.fromInitECI(self.GEO_TEST_RSO, self.GEO_TEST_ECI)
        assert station_keeper.interruptRequired(0.0, self.GEO_TEST_ECI) is False
        assert station_keeper(0.0, self.GEO_TEST_ECI) != 0

    def testGeoEastWestInterruptRequired(self, ):
        """Validate that the GEO East-West station keeper object correctly requires interrupt."""
        station_keeper = station_keeping.KeepGeoEastWest.fromInitECI(self.GEO_TEST_RSO, self.GEO_TEST_ECI)

        geo_lla = transforms.ecef2lla(transforms.eci2ecef(self.GEO_TEST_ECI))
        geo_lla[1] += station_keeping.KeepGeoEastWest.LON_DRIFT_THRESHOLD * 1.1
        new_state = transforms.ecef2eci(transforms.lla2ecef(geo_lla))

        assert station_keeper.interruptRequired(0.0, new_state) is True
        assert station_keeper(0.0, new_state) == 0

    def testGeoEastWestPropagation(self, dynamics_obj):
        """Validate that the GEO East-West station keeping maneuver executes when it's supposed to."""
        station_keeper = station_keeping.KeepGeoEastWest.fromInitECI(self.GEO_TEST_RSO, self.GEO_TEST_ECI)
        dynamics_obj.propagate(0.0, self.PROPAGATE_DURATION, self.GEO_TEST_ECI, station_keeping=[station_keeper])
        assert station_keeper.getActivationDetails() != (None, None)

    def testGeoNorthSouthInit(self, ):
        """Validate that the GEO North-South station keeper object can be correctly instantiated."""
        station_keeper = station_keeping.KeepGeoNorthSouth.fromInitECI(self.GEO_TEST_RSO, self.GEO_TEST_ECI)
        assert np.array_equal(station_keeper.initial_eci, self.GEO_TEST_ECI)
        assert station_keeper.initial_coe == Orbit.rv2coe(self.GEO_TEST_ECI)
        assert station_keeper.ntw_delta_v == 0.0

    def testGeoNorthSouthInterruptNotRequired(self, ):
        """Validate that the GEO North-South station keeper object doesn't incorrectly require interrupt."""
        station_keeper = station_keeping.KeepGeoNorthSouth.fromInitECI(self.GEO_TEST_RSO, self.GEO_TEST_ECI)
        assert station_keeper.interruptRequired(0.0, self.GEO_TEST_ECI) is False
        assert station_keeper(0.0, self.GEO_TEST_ECI) != 0

    def testGeoNorthSouthInterruptRequired(self, ):
        """Validate that the GEO North-South station keeper object correctly requires interrupt."""
        station_keeper = station_keeping.KeepGeoNorthSouth.fromInitECI(self.GEO_TEST_RSO, self.GEO_TEST_ECI)

        geo_lla = transforms.ecef2lla(transforms.eci2ecef(self.GEO_TEST_ECI))
        geo_lla[0] += station_keeping.KeepGeoNorthSouth.LAT_DRIFT_THRESHOLD * 1.1
        new_state = transforms.ecef2eci(transforms.lla2ecef(geo_lla))

        assert station_keeper.interruptRequired(0.0, new_state) is True
        assert station_keeper(0.0, new_state) == 0
        assert norm(station_keeper.getStateChange(0, new_state)[3:]) > 0

    @pytest.mark.skip(reason="safeArccos() assertion")
    def testGeoNorthSouthPropagation(self, dynamics_obj):
        """Validate that the GEO North-South station keeping maneuver executes when it's supposed to."""
        station_keeper = station_keeping.KeepGeoNorthSouth.fromInitECI(self.GEO_TEST_RSO, self.GEO_TEST_ECI)

        geo_lla = transforms.ecef2lla(transforms.eci2ecef(self.GEO_TEST_ECI))
        geo_lla[0] += station_keeping.KeepGeoNorthSouth.LAT_DRIFT_THRESHOLD
        new_eci = transforms.ecef2eci(transforms.lla2ecef(geo_lla))

        dynamics_obj.propagate(0.0, self.PROPAGATE_DURATION, new_eci, station_keeping=[station_keeper])
        assert station_keeper.getActivationDetails() != (None, None)
