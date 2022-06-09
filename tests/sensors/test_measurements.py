# pylint: disable=attribute-defined-outside-init, no-self-use
# Standard Library Imports
import datetime
# Third Party Imports
import numpy as np
import pytest
# RESONAATE Imports
try:
    import resonaate.physics.constants as const
    from resonaate.sensors.measurements import getAzimuth, getElevation, getRange
    from resonaate.sensors.measurements import getAzimuthRate, getElevationRate, getRangeRate
    from resonaate.physics.time.stardate import JulianDate
    from resonaate.physics.transforms.eops import EarthOrientationParameter
    from resonaate.physics.transforms.methods import lla2ecef, getSlantRangeVector
    from resonaate.physics.transforms.reductions import updateReductionParameters
except ImportError as error:
    raise Exception(
        f"Please ensure you have appropriate packages installed:\n {error}"
    ) from error
# Testing Imports
from ..conftest import BaseTestCase


class TestMeasurements(BaseTestCase):
    """Test all functions in measurements module."""

    # Vallado example 4-1 (pg. 273), second part
    eci = np.asarray(
        [
            5036.736529, -10806.660797, -4534.633784,
            2.6843855, -5.7595920, -2.4168093
        ]
    )
    true_rng = 11710.812
    true_az = np.radians(210.8777747)
    true_el = np.radians(-5.9409535)
    true_rng_rt = 6.0842826
    true_az_rt = np.radians(0.00384011466)
    true_el_rt = np.radians(0.01495847759)

    # Vallado example 4-1
    lla = np.asarray([np.radians(39.007), np.radians(-104.883), 2.19456])
    julian_date = JulianDate.getJulianDate(1994, 5, 14, 13, 11, 20.59856)

    # From celestrak.com for May 14, 1994
    # 1994 05 14 49486  0.189443  0.306064 -0.1279402  0.0021743 -0.016163 -0.008660  0.000187  0.000039  28
    eops = EarthOrientationParameter(
        datetime.date(1994, 5, 14),
        0, 0,
        -0.016163 * const.ARCSEC2RAD, -0.008660 * const.ARCSEC2RAD,
        0, 0.0021743, 28
    )

    @pytest.fixture(scope="function", name="sez_state")
    def convertToSEZ(self, redis):  # pylint: disable=unused-argument
        """Fixture to get properly converted SEZ observation vector."""
        updateReductionParameters(self.julian_date, eops=self.eops)
        yield getSlantRangeVector(lla2ecef(self.lla), self.eci)

    def testMeasurements(self, sez_state):
        """Test measurements for az, el, range & their rates."""
        assert np.isclose(self.true_az, getAzimuth(sez_state))
        assert np.isclose(self.true_el, getElevation(sez_state))
        assert np.isclose(self.true_rng, getRange(sez_state))
        assert np.isclose(self.true_az_rt, getAzimuthRate(sez_state))
        assert np.isclose(self.true_el_rt, getElevationRate(sez_state))
        assert np.isclose(self.true_rng_rt, getRangeRate(sez_state))
