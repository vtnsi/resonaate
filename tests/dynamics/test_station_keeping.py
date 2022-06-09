# pylint: disable=attribute-defined-outside-init
# Standard Library Imports
# Third Party Imports
import numpy as np
import pytest
from scipy.linalg import norm

try:
    # RESONAATE Imports
    from resonaate.dynamics.integration_events import station_keeping
    from resonaate.physics import constants as const
    from resonaate.physics.bodies import Earth
    from resonaate.physics.orbits.elements import ClassicalElements
    from resonaate.physics.transforms import methods as transforms
    from resonaate.physics.transforms.reductions import getReductionParameters
    from resonaate.scenario.clock import updateReductionParameters
except ImportError as error:
    raise Exception(f"Please ensure you have appropriate packages installed:\n {error}") from error
# Local Imports
# Testing Imports
from ..conftest import TEST_START_JD, BaseTestCase


@pytest.fixture(autouse=True)
def _updateParams():
    """Make sure reduction parameters and third body positions are up to date."""
    updateReductionParameters(TEST_START_JD)


class TestStationKeeping(BaseTestCase):
    """Collection of unit tests to validate station keeping."""

    PROPAGATE_DURATION = 60 * 60

    LEO_TEST_RSO = 41858
    LEO_TEST_ECI = np.asarray([6878.038277, -33.799030, -14.685957, 0.037408, 7.612516, -0.000253])

    GEO_TEST_RSO = 27414
    GEO_TEST_ECI = np.asarray(
        [
            7772.578605391435,
            41451.327150257275,
            -13.013957256406881,
            -3.0166132050756818,
            0.566000461604396,
            0.17125923555827943,
        ]
    )

    def testKeepLeoUpInit(self):
        """Validate that the LEO station keeper object can be correctly instantiated."""
        station_keeper = station_keeping.KeepLeoUp.fromInitECI(
            self.LEO_TEST_RSO, self.LEO_TEST_ECI, TEST_START_JD
        )
        station_keeper.reductions = getReductionParameters()
        assert np.array_equal(station_keeper.initial_eci, self.LEO_TEST_ECI)
        assert station_keeper.initial_coe == ClassicalElements.fromECI(self.LEO_TEST_ECI)
        assert station_keeper.ntw_delta_v == 0.0

    def testKeepLeoUpInterruptNotRequired(self):
        """Validate that the LEO station keeper object doesn't incorrectly require interrupt."""
        station_keeper = station_keeping.KeepLeoUp.fromInitECI(
            self.LEO_TEST_RSO, self.LEO_TEST_ECI, TEST_START_JD
        )
        station_keeper.reductions = getReductionParameters()
        assert station_keeper.interruptRequired(0.0, self.LEO_TEST_ECI) is False
        assert station_keeper(0.0, self.LEO_TEST_ECI) != 0

    def testKeepLeoUpInterruptRequired(self):
        """Validate that the LEO station keeper object correctly requires interrupt."""
        station_keeper = station_keeping.KeepLeoUp.fromInitECI(
            self.LEO_TEST_RSO, self.LEO_TEST_ECI, TEST_START_JD
        )
        station_keeper.reductions = getReductionParameters()
        coe = ClassicalElements.fromECI(self.LEO_TEST_ECI)
        coe.sma -= station_keeping.KeepLeoUp.ALT_DRIFT_THRESHOLD * 1.01
        coe.semilatus_rectum = coe.sma * (1 - coe.ecc**2)
        coe.period = 2 * const.PI * np.sqrt(coe.sma**3 / Earth.mu)
        new_state = coe.toECI()
        assert station_keeper.interruptRequired(0.0, new_state) is True
        assert station_keeper(0.0, new_state) == 0

    def testKeepLeoUpPropagation(self, dynamics):
        """Validate that the LEO station keeping maneuver executes when it's supposed to."""
        station_keeper = station_keeping.KeepLeoUp.fromInitECI(
            self.LEO_TEST_RSO, self.LEO_TEST_ECI, TEST_START_JD
        )
        station_keeper.reductions = getReductionParameters()
        leo_lla = transforms.ecef2lla(transforms.eci2ecef(self.LEO_TEST_ECI))
        leo_lla[2] -= station_keeping.KeepLeoUp.ALT_DRIFT_THRESHOLD * 1.01
        new_eci = transforms.ecef2eci(transforms.lla2ecef(leo_lla))
        dynamics.propagate(0.0, self.PROPAGATE_DURATION, new_eci, station_keeping=[station_keeper])
        assert station_keeper.getActivationDetails() != (None, None)

    def testGeoEastWestInit(self):
        """Validate that the GEO East-West station keeper object can be correctly instantiated."""
        station_keeper = station_keeping.KeepGeoEastWest.fromInitECI(
            self.GEO_TEST_RSO, self.GEO_TEST_ECI, TEST_START_JD
        )
        station_keeper.reductions = getReductionParameters()
        assert np.array_equal(station_keeper.initial_eci, self.GEO_TEST_ECI)
        assert station_keeper.initial_coe == ClassicalElements.fromECI(self.GEO_TEST_ECI)
        assert station_keeper.ntw_delta_v == 0.0

    def testGeoEastWestInterruptNotRequired(self):
        """Validate that the GEO East-West station keeper object doesn't incorrectly require interrupt."""
        station_keeper = station_keeping.KeepGeoEastWest.fromInitECI(
            self.GEO_TEST_RSO, self.GEO_TEST_ECI, TEST_START_JD
        )
        station_keeper.reductions = getReductionParameters()
        assert station_keeper.interruptRequired(0.0, self.GEO_TEST_ECI) is False
        assert station_keeper(0.0, self.GEO_TEST_ECI) != 0

    def testGeoEastWestInterruptRequired(self):
        """Validate that the GEO East-West station keeper object correctly requires interrupt."""
        station_keeper = station_keeping.KeepGeoEastWest.fromInitECI(
            self.GEO_TEST_RSO, self.GEO_TEST_ECI, TEST_START_JD
        )
        station_keeper.reductions = getReductionParameters()
        geo_lla = transforms.ecef2lla(transforms.eci2ecef(self.GEO_TEST_ECI))
        geo_lla[1] += station_keeping.KeepGeoEastWest.LON_DRIFT_THRESHOLD * 1.01
        new_state = transforms.ecef2eci(transforms.lla2ecef(geo_lla))

        assert station_keeper.interruptRequired(0.0, new_state) is True
        assert station_keeper(0.0, new_state) == 0

    def testGeoEastWestPropagation(self, dynamics):
        """Validate that the GEO East-West station keeping maneuver executes when it's supposed to."""
        station_keeper = station_keeping.KeepGeoEastWest.fromInitECI(
            self.GEO_TEST_RSO, self.GEO_TEST_ECI, TEST_START_JD
        )
        station_keeper.reductions = getReductionParameters()
        geo_lla = transforms.ecef2lla(transforms.eci2ecef(self.GEO_TEST_ECI))
        geo_lla[1] += station_keeping.KeepGeoEastWest.LON_DRIFT_THRESHOLD * 1.01
        new_state = transforms.ecef2eci(transforms.lla2ecef(geo_lla))

        dynamics.propagate(
            0.0, self.PROPAGATE_DURATION, new_state, station_keeping=[station_keeper]
        )
        assert station_keeper.getActivationDetails() != (None, None)

    def testGeoNorthSouthInit(self):
        """Validate that the GEO North-South station keeper object can be correctly instantiated."""
        station_keeper = station_keeping.KeepGeoNorthSouth.fromInitECI(
            self.GEO_TEST_RSO, self.GEO_TEST_ECI, TEST_START_JD
        )
        station_keeper.reductions = getReductionParameters()
        assert np.array_equal(station_keeper.initial_eci, self.GEO_TEST_ECI)
        assert station_keeper.initial_coe == ClassicalElements.fromECI(self.GEO_TEST_ECI)
        assert station_keeper.ntw_delta_v == 0.0

    def testGeoNorthSouthInterruptNotRequired(self):
        """Validate that the GEO North-South station keeper object doesn't incorrectly require interrupt."""
        station_keeper = station_keeping.KeepGeoNorthSouth.fromInitECI(
            self.GEO_TEST_RSO, self.GEO_TEST_ECI, TEST_START_JD
        )
        station_keeper.reductions = getReductionParameters()
        station_keeper.julian_date_start = TEST_START_JD
        assert station_keeper.interruptRequired(0.0, self.GEO_TEST_ECI) is False
        assert station_keeper(0.0, self.GEO_TEST_ECI) != 0

    def testGeoNorthSouthInterruptRequired(self):
        """Validate that the GEO North-South station keeper object correctly requires interrupt."""
        station_keeper = station_keeping.KeepGeoNorthSouth.fromInitECI(
            self.GEO_TEST_RSO, self.GEO_TEST_ECI, TEST_START_JD
        )
        station_keeper.reductions = getReductionParameters()
        geo_lla = transforms.ecef2lla(transforms.eci2ecef(self.GEO_TEST_ECI))
        geo_lla[0] += station_keeping.KeepGeoNorthSouth.LAT_DRIFT_THRESHOLD * 1.01
        new_state = transforms.ecef2eci(transforms.lla2ecef(geo_lla))
        assert station_keeper.interruptRequired(0.0, new_state) is True
        assert station_keeper(0.0, new_state) == 0
        assert norm(station_keeper.getStateChange(0, new_state)[3:]) > 0

    def testGeoNorthSouthPropagation(self, dynamics):
        """Validate that the GEO North-South station keeping maneuver executes when it's supposed to."""
        station_keeper = station_keeping.KeepGeoNorthSouth.fromInitECI(
            self.GEO_TEST_RSO, self.GEO_TEST_ECI, TEST_START_JD
        )
        station_keeper.reductions = getReductionParameters()
        geo_lla = transforms.ecef2lla(transforms.eci2ecef(self.GEO_TEST_ECI))
        geo_lla[0] += station_keeping.KeepGeoNorthSouth.LAT_DRIFT_THRESHOLD * 1.2
        new_eci = transforms.ecef2eci(transforms.lla2ecef(geo_lla))
        dynamics.propagate(0.0, self.PROPAGATE_DURATION, new_eci, station_keeping=[station_keeper])
        assert station_keeper.getActivationDetails() != (None, None)
