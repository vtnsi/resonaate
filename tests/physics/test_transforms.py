# pylint: disable=attribute-defined-outside-init, no-self-use
# Standard Library Imports
import datetime
# Third Party Imports
import numpy as np
import pytest
# RESONAATE Imports
try:
    import resonaate.physics.constants as const
    from resonaate.physics.time.stardate import JulianDate
    from resonaate.physics.transforms.eops import EarthOrientationParameter
    from resonaate.physics.transforms.methods import eci2ecef, ecef2eci
    from resonaate.physics.transforms.reductions import updateReductionParameters
except ImportError as error:
    raise Exception(
        "Please ensure you have appropriate packages installed:\n {0}".format(error)
    ) from error
# Testing Imports
from ..conftest import BaseTestCase


class TestTransforms(BaseTestCase):
    """Test cases for validating the `physics.transforms` package."""

    @pytest.fixture(scope="function", autouse=True)
    def setUp(self, redis):  # pylint: disable=unused-argument
        """Prepare the test fixture."""
        # Correct values, taken from Vallado examples
        self.r_itrf = np.asarray([-1033.4793830, 7901.2952754, 6380.3565958])  # km
        self.v_itrf = np.asarray([-3.225636520, -2.872451450, 5.531924446])  # km/sec

        self.r_gcrf = np.asarray([5102.5089579, 6123.0114007, 6378.1369282])  # km
        self.v_gcrf = np.asarray([-4.743220157, 0.790536497, 5.533755727])  # km/sec

        # Given UTC
        year, month, day, hour, minute, second = 2004, 4, 6, 7, 51, 28.386009
        # Julian date & Julian date at 0 hrs
        self.julian_date = JulianDate.getJulianDate(year, month, day, hour, minute, second)
        # Given polar motion (arcsec -> rad)
        x_p = -0.140682 * const.ARCSEC2RAD
        y_p = 0.333309 * const.ARCSEC2RAD

        # Given UT1-UTC (s)
        dut1 = -0.4399619
        # Given Nut corrections wrt IAU 1976/1980 (arcsec->rad)
        ddp80 = -0.052195 * const.ARCSEC2RAD
        dde80 = -0.003875 * const.ARCSEC2RAD
        # Given delta atomic time (s)
        dat = 32.0
        # Given length of day (s)
        lod = 0.0015563

        # Calculate the required parameters
        self.eops = EarthOrientationParameter(
            datetime.date(year, month, day), x_p, y_p, ddp80, dde80, dut1, lod, dat
        )
        # Actually update with our test values
        updateReductionParameters(self.julian_date, eops=self.eops)

    def testEci2Ecef(self):
        """Test conversion from ECI (inertial) to ECEF (fixed)."""
        ecef_state = eci2ecef(
            np.concatenate((self.r_gcrf, self.v_gcrf), axis=0)
        )
        assert isinstance(ecef_state, np.ndarray)
        assert ecef_state.shape == (6, )
        assert np.allclose(
            ecef_state[:3],
            self.r_itrf,
            atol=1e-11,
            rtol=1e-8
        )
        assert np.allclose(
            ecef_state[3:],
            self.v_itrf,
            atol=1e-9,
            rtol=1e-6
        )

    def testEcef2Eci(self):
        """Test conversion from ECEF (fixed) to ECI (inertial)."""
        eci_state = ecef2eci(
            np.concatenate((self.r_itrf, self.v_itrf), axis=0)
        )
        assert isinstance(eci_state, np.ndarray)
        assert eci_state.shape == (6, )
        assert np.allclose(
            eci_state[:3],
            self.r_gcrf,
            atol=1e-11,
            rtol=1e-8
        )
        assert np.allclose(
            eci_state[3:],
            self.v_gcrf,
            atol=1e-9,
            rtol=1e-6
        )
