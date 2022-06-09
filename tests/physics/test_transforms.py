# pylint: disable=attribute-defined-outside-init, no-self-use
# Standard Library Imports
# Third Party Imports
from numpy import asarray, allclose, isclose, matmul, ndarray, concatenate
import pytest
# RESONAATE Imports
try:
    import resonaate.physics.constants as const
    from resonaate.physics.time.stardate import JulianDate
    from resonaate.physics.time.conversions import utc2TerrestrialTime
    from resonaate.physics.transforms.methods import eci2ecef, ecef2eci
    from resonaate.physics.transforms.reductions import updateReductionParameters, getReductionParameters
except ImportError as error:
    raise Exception(
        "Please ensure you have appropriate packages installed:\n {0}".format(error)
    ) from error
# Testing Imports
from ..conftest import BaseTestCase


class TestFK5Reduction(BaseTestCase):
    """Test cases for validating the `physics.transformas` package."""

    @pytest.fixture(scope="function", autouse=True)
    def setUp(self):
        """Prepare the test fixture."""
        # Correct values, taken from Vallado examples
        self.r_itrf = asarray([-1033.4793830, 7901.2952754, 6380.3565958])  # km
        self.v_itrf = asarray([-3.225636520, -2.872451450, 5.531924446])  # km/sec

        self.r_gcrf = asarray([5102.5089579, 6123.0114007, 6378.1369282])  # km
        self.v_gcrf = asarray([-4.743220157, 0.790536497, 5.533755727])  # km/sec

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
        self.eops = {
            "xp": x_p,
            "yp": y_p,
            "dut1": dut1,
            "lod": lod,
            "ddPsi": ddp80,
            "ddEps": dde80,
            "dAT": dat
        }
        # Actually update with our test values
        updateReductionParameters(self.julian_date, eops=self.eops)

    def testTransform(self):
        """Numerically validate reduction algorithm against results from IERS."""
        # pylint: disable=too-many-locals
        # Correct values, taken from IERS examples
        correct_tt = 54195.500754444444444
        correct_ut1 = 54195.499999165813831
        correct_np_mat = asarray(
            [
                [0.999998403176203, -0.001639032970562, -0.000712190961847],
                [0.001639000942243, 0.999998655799521, -0.000045552846624],
                [0.000712264667137, 0.000044385492226, 0.999999745354454],
            ]
        )
        correct_rnp_mat = asarray(
            [
                [0.973104317592265, 0.230363826166883, -0.000703332813776],
                [-0.230363798723533, 0.973104570754697, 0.000120888299841],
                [0.000712264667137, 0.000044385492226, 0.999999745354454],
            ]
        )
        correct_full_mat = asarray(
            [
                [0.973104317712772, 0.230363826174782, -0.000703163477127],
                [-0.230363800391868, 0.973104570648022, 0.000118545116892],
                [0.000711560100206, 0.000046626645796, 0.999999745754058],
            ]
        )

        # Given UTC
        year, month, day, hour, minute, second = 2007, 4, 5, 12, 0, 0.0
        # Given Julian date & Julian date at 0 hrs
        julian_date = JulianDate.getJulianDate(year, month, day, hour, minute, second)
        julian_day = JulianDate.getJulianDate(year, month, day, 0, 0, 0)
        # Given Polar motion (arcsec -> rad)
        x_p = 0.0349282 * const.ARCSEC2RAD
        y_p = 0.4833163 * const.ARCSEC2RAD
        # Given UT1-UTC (s)
        dut1 = -0.072073685
        # Given Nut corrections wrt IAU 1976/1980 (mas->rad)
        ddp80 = -55.0655 * const.ARCSEC2RAD / 1000
        dde80 = -6.3580 * const.ARCSEC2RAD / 1000
        # Given delta atomic time (s)
        dat = 33.0

        # Time checks [TODO]: Move this check to conversions unit-test
        _, ttt = utc2TerrestrialTime(year, month, day, hour, minute, second, dat)
        assert isclose(ttt * 36525 + 2451545 - 2400000.5, correct_tt)  # places=9
        utc = hour * 3600 + minute * 60 + second
        tut = utc + dut1
        ut1 = julian_day + tut * const.SEC2DAYS
        assert isclose(ut1 - 2400000.5, correct_ut1)  # places=9

        # Calculate the required parameters
        eops = {
            "xp": x_p,
            "yp": y_p,
            "dut1": dut1,
            "lod": 0.00001,
            "ddPsi": ddp80,
            "ddEps": dde80,
            "dAT": dat
        }
        # (rot_pn, rot_pnr, rot_rnp, rot_w, rot_wt, eops, gast, eq_equinox)
        updateReductionParameters(julian_date, eops=eops)
        params = getReductionParameters()
        rot_wt = params["rot_wt"]
        rot_rnp = params["rot_rnp"]
        rot_np = params["rot_pn"].T

        # Implement the full rotation from terrestrial (ITRF) to celestial (GCRF)
        full_mat = matmul(rot_wt, rot_rnp)

        # Compare versus results given in document
        assert allclose(
            correct_np_mat,
            rot_np,
            atol=1e-10,
            rtol=1e-9
        )
        assert allclose(
            correct_rnp_mat,
            rot_rnp,
            atol=1e-10,
            rtol=1e-9
        )
        assert allclose(
            correct_full_mat,
            full_mat,
            atol=1e-10,
            rtol=1e-9
        )

    def testValidJulianDate(self):
        """Test reduction algorithm using only :class:`.JulianDate` as input."""
        # Julian date
        julian_date = JulianDate.getJulianDate(2018, 3, 15, 12, 55, 33.78)
        # (rot_pn, rot_pnr, rot_rnp, rot_w, rot_wt, eops, gast, eq_equinox)
        updateReductionParameters(julian_date)
        params = getReductionParameters()
        rot_w = params["rot_w"]
        rot_pn = params["rot_pn"]

        # Assert that we get 3x3 numpy arrays back
        assert isinstance(rot_pn, ndarray)
        assert isinstance(rot_w, ndarray)
        assert rot_pn.shape == (3, 3)
        assert rot_w.shape == (3, 3)

    def testInvalidJulianDate(self):
        """Test catching a bad :class:`.JulianDate` objects."""
        # Ridiculous Julian date
        julian_date = JulianDate(3)
        with pytest.raises(ValueError):
            updateReductionParameters(julian_date)

        # Less ridiculous Julian date, but before range of EOPs
        julian_date = JulianDate.getJulianDate(2000, 1, 24, 7, 23, 56.9)
        with pytest.raises(ValueError):
            updateReductionParameters(julian_date)

        # Less ridiculous Julian date, but after range of EOPs
        julian_date = JulianDate.getJulianDate(2050, 1, 24, 7, 23, 56.9)
        with pytest.raises(ValueError):
            updateReductionParameters(julian_date)

    def testEci2Ecef(self):
        """Test conversion from ECI (inertial) to ECEF (fixed)."""
        ecef_state = eci2ecef(
            concatenate((self.r_gcrf, self.v_gcrf), axis=0)
        )
        assert isinstance(ecef_state, ndarray)
        assert ecef_state.shape == (6, )
        assert allclose(
            ecef_state[:3],
            self.r_itrf,
            atol=1e-11,
            rtol=1e-8
        )
        assert allclose(
            ecef_state[3:],
            self.v_itrf,
            atol=1e-9,
            rtol=1e-6
        )

    def testEcef2Eci(self):
        """Test conversion from ECEF (fixed) to ECI (inertial)."""
        eci_state = ecef2eci(
            concatenate((self.r_itrf, self.v_itrf), axis=0)
        )
        assert isinstance(eci_state, ndarray)
        assert eci_state.shape == (6, )
        assert allclose(
            eci_state[:3],
            self.r_gcrf,
            atol=1e-11,
            rtol=1e-8
        )
        assert allclose(
            eci_state[3:],
            self.v_gcrf,
            atol=1e-9,
            rtol=1e-6
        )
