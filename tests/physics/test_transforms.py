from __future__ import annotations

# Standard Library Imports
import datetime

# Third Party Imports
import numpy as np
import pytest

# RESONAATE Imports
import resonaate.physics.constants as const
from resonaate.physics.maths import rot1, rot3
from resonaate.physics.orbits.elements import ClassicalElements
from resonaate.physics.orbits.utils import getFlightPathAngle
from resonaate.physics.time.stardate import JulianDate
from resonaate.physics.transforms.eops import (
    EarthOrientationParameter,
    setEarthOrientationParameters,
)
from resonaate.physics.transforms.methods import (
    cartesian2spherical,
    ecef2eci,
    ecef2lla,
    eci2ecef,
    eci2razel,
    eci2rsw,
    eci2sez,
    geocentric2geodetic,
    geodetic2geocentric,
    getSlantRangeVector,
    lla2ecef,
    ntw2eci,
    radec2razel,
    razel2radec,
    razel2sez,
    rsw2eci,
    sez2ecef,
    sez2eci,
    spherical2cartesian,
)


class TestECI:
    """Test cases for validating the ECI transforms."""

    @pytest.fixture(autouse=True)
    def _setUpECITransforms(self):
        """Prepare the test fixture."""
        # Correct values, taken from Vallado examples
        self.r_itrf = np.asarray([-1033.4793830, 7901.2952754, 6380.3565958])  # km
        self.v_itrf = np.asarray([-3.225636520, -2.872451450, 5.531924446])  # km/sec

        self.r_gcrf = np.asarray([5102.5089579, 6123.0114007, 6378.1369282])  # km
        self.v_gcrf = np.asarray([-4.743220157, 0.790536497, 5.533755727])  # km/sec

        # Given UTC
        year, month, day, hour, minute, second, microsecond = 2004, 4, 6, 7, 51, 28, 386009
        # Julian date & Julian date at 0 hrs
        self.calendar_date = datetime.datetime(year, month, day, hour, minute, second, microsecond)
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
            datetime.date(year, month, day),
            x_p,
            y_p,
            ddp80,
            dde80,
            dut1,
            lod,
            dat,
        )
        # Actually update with our test values
        setEarthOrientationParameters(self.eops.date, self.eops)

    def testEci2Ecef(self):
        """Test conversion from ECI (inertial) to ECEF (fixed)."""
        ecef_state = eci2ecef(
            np.concatenate((self.r_gcrf, self.v_gcrf), axis=0),
            self.calendar_date,
        )
        assert isinstance(ecef_state, np.ndarray)
        assert ecef_state.shape == (6,)
        assert np.allclose(ecef_state[:3], self.r_itrf, atol=1e-11, rtol=1e-8)
        assert np.allclose(ecef_state[3:], self.v_itrf, atol=1e-9, rtol=1e-6)

    def testEcef2Eci(self):
        """Test conversion from ECEF (fixed) to ECI (inertial)."""
        eci_state = ecef2eci(
            np.concatenate((self.r_itrf, self.v_itrf), axis=0),
            self.calendar_date,
        )
        assert isinstance(eci_state, np.ndarray)
        assert eci_state.shape == (6,)
        assert np.allclose(eci_state[:3], self.r_gcrf, atol=1e-11, rtol=1e-8)
        assert np.allclose(eci_state[3:], self.v_gcrf, atol=1e-9, rtol=1e-6)


class TestSatelliteFrames:
    """Test cases for validating the transforms for satellite-defined frames."""

    ORBITAL_ELEMENTS = np.asarray(
        [
            [500, 0.001, np.deg2rad(40), np.deg2rad(10), np.deg2rad(100), np.deg2rad(0)],
            [500, 0.001, np.deg2rad(40), np.deg2rad(10), np.deg2rad(100), np.deg2rad(90)],
            [500, 0.001, np.deg2rad(40), np.deg2rad(10), np.deg2rad(100), np.deg2rad(180)],
            [500, 0.001, np.deg2rad(40), np.deg2rad(10), np.deg2rad(100), np.deg2rad(270)],
        ],
    )

    x_ntw = np.asarray([0.1, 0.2, -0.05, 0.00001, -0.00004, 0.000003])

    x_rsw = np.asarray([0.1, 0.2, -0.05, 0.00001, -0.00004, 0.000003])

    @pytest.mark.parametrize("elements", ORBITAL_ELEMENTS)
    def testNtw2Eci(self, elements):
        """Test rotation of NTW state to ECI."""
        orbit = ClassicalElements(*elements)
        x_eci = orbit.toECI()
        rel_eci = ntw2eci(x_eci, self.x_ntw)

        # Known transform using angles
        ntw2eci_rot = np.linalg.multi_dot(
            [
                rot3(-1.0 * orbit.raan),
                rot1(-1.0 * orbit.inc),
                rot3(-1.0 * (orbit.argp + orbit.true_anomaly)),
                rot3(getFlightPathAngle(orbit.ecc, orbit.true_anomaly)),
            ],
        )
        correct_pos = ntw2eci_rot.dot(self.x_ntw[:3])
        correct_vel = ntw2eci_rot.dot(self.x_ntw[3:])

        assert np.allclose(
            rel_eci,
            np.concatenate([correct_pos, correct_vel], axis=0),
            atol=1e-9,
            rtol=1e-6,
        )

    @pytest.mark.parametrize("elements", ORBITAL_ELEMENTS)
    def testRsw2Eci(self, elements):
        """Test rotation of RSW state to ECI."""
        orbit = ClassicalElements(*elements)
        x_eci = orbit.toECI()
        rel_eci = rsw2eci(x_eci, self.x_rsw)

        # Known transform using angles
        rsw2eci_rot = np.linalg.multi_dot(
            [
                rot3(-1.0 * orbit.raan),
                rot1(-1.0 * orbit.inc),
                rot3(-1.0 * (orbit.argp + orbit.true_anomaly)),
            ],
        )
        correct_pos = rsw2eci_rot.dot(self.x_rsw[:3])
        correct_vel = rsw2eci_rot.dot(self.x_rsw[3:])

        assert np.allclose(
            rel_eci,
            np.concatenate([correct_pos, correct_vel], axis=0),
            atol=1e-9,
            rtol=1e-6,
        )

    @pytest.mark.parametrize("elements", ORBITAL_ELEMENTS)
    def testEci2Rsw(self, elements):
        """Test rotation of ECI chaser state to RSW."""
        orbit = ClassicalElements(*elements)
        x_eci = orbit.toECI()
        # Known transform using angles
        eci2rsw_rot = np.linalg.multi_dot(
            [
                rot3(-1.0 * (orbit.argp + orbit.true_anomaly)).T,
                rot1(-1.0 * orbit.inc).T,
                rot3(-1.0 * orbit.raan).T,
            ],
        )
        chaser_relative_eci_state = np.asarray([0.1, 0.2, -0.05, 0.00001, -0.00004, 0.000003])
        chaser_rsw = eci2rsw(
            target_eci=x_eci,
            chaser_eci=x_eci + chaser_relative_eci_state,
        )
        correct_pos = eci2rsw_rot.dot(chaser_relative_eci_state[:3])
        correct_vel = eci2rsw_rot.dot(chaser_relative_eci_state[3:])

        assert np.allclose(
            chaser_rsw,
            np.concatenate([correct_pos, correct_vel], axis=0),
            atol=1e-9,
            rtol=1e-6,
        )


class TestLLA:
    """Test cases for validating the LLA transforms."""

    LLA_EDGE_CASES = np.asarray(
        [
            [6379, 1, 0.0, -5, 1, 3],  # equator
            [0.0, 0.0, 0.0, -5, 1, 3],  # equator & 0 deg lat/lon
        ],
    )

    @pytest.fixture(autouse=True)
    def _setUpLLA(self):
        """Fixture to setup LLA conversion tests."""
        # Vallado example 4-1 (pg. 273), second part
        self.eci = np.asarray(
            [5036.736529, -10806.660797, -4534.633784, 2.6843855, -5.7595920, -2.4168093],
        )

        # Vallado example 4-1
        self.lla = np.asarray([np.radians(39.007), np.radians(-104.883), 2.187])
        self.julian_date = JulianDate.getJulianDate(1995, 5, 20, 3, 17, 2.0)

        # From celestrak.com for May 20, 1995
        # 1995 05 20 49857  0.195561  0.514152  0.0231557  0.0025598 -0.022064 -0.008907 -0.000041  0.000147  29
        self.eops = EarthOrientationParameter(
            datetime.date(1995, 5, 20),
            0,
            0,
            -0.022064 * const.ARCSEC2RAD,
            -0.008907 * const.ARCSEC2RAD,
            0.0,
            0.0025598,
            29,
        )
        setEarthOrientationParameters(datetime.date(1995, 5, 20), self.eops)

    @pytest.mark.parametrize("ecef", LLA_EDGE_CASES)
    def testLLAEdgeCases(self, ecef):
        """Test converting to LLA with  0 values."""
        assert not np.isnan(ecef2lla(ecef)).any()

    def testConvertToGeocentricLatitude(self):
        """Test converting geodetic latitude to geocentric latitude."""
        # Vallado example 3-1
        assert np.isclose(geodetic2geocentric(np.radians(34.352496)), np.radians(34.173429))

    def testConvertToGeodeticLatitude(self):
        """Test converting geocentric latitude to geodetic latitude."""
        # Vallado example 3-1
        assert np.isclose(geocentric2geodetic(np.radians(34.173429)), np.radians(34.352496))

    def testLLA(self):
        """Test converting LLA to ECEF and back."""
        # Vallado example 7-1
        ecef = lla2ecef(self.lla)
        assert np.allclose(
            ecef,
            np.asarray([-1275.1219, -4797.9890, 3994.2975, 0, 0, 0]),
            atol=1e-9,
            rtol=1e-6,
        )
        assert np.allclose(ecef2lla(ecef), self.lla, atol=1e-9, rtol=1e-6)


class TestRaDecRazelSEZ:
    """Test cases for validating the radec & razel transforms."""

    SPHERICAL_2_CARTESIAN = np.asarray(
        [
            np.linspace(0.1, 40000, 10),
            np.radians(np.linspace(-90, 90, 10)),
            np.radians(np.linspace(0, 360, 10)),
            np.linspace(-5, 5, 10),
            np.linspace(-1, 1, 10),
            np.linspace(-1, 1, 10),
        ],
    ).T

    @pytest.fixture(autouse=True)
    def _setUpRaDecTests(self):
        """Fixture for setting test values for RaDec tests."""
        # Vallado example 4-1 (pg. 273), second part
        self.true_radec_geo = np.asarray(
            [
                12756,
                np.radians(-20.8234944),
                np.radians(294.9891458),
                6.7985140,
                np.radians(-0.00000001794),
                np.radians(-0.00000012244),
            ],
        )
        self.true_radec_topo = np.asarray(
            [
                11710.812,
                np.radians(-46.7583402),
                np.radians(276.9337329),
                6.0842826,
                np.radians(0.01439246203),
                np.radians(0.01233970405),
            ],
        )
        self.true_azel = np.asarray(
            [
                11710.812,
                np.radians(-5.9409535),
                np.radians(210.8777747),
                6.0842826,
                np.radians(0.01495847759),
                np.radians(0.00384011466),
            ],
        )
        self.lla = np.asarray([np.radians(39.007), np.radians(-104.883), 2.19456])
        self.calendar_date = datetime.datetime(1994, 5, 14, 13, 11, 20, 598560)
        self.eci = np.asarray(
            [5036.736529, -10806.660797, -4534.633784, 2.6843855, -5.7595920, -2.4168093],
        )
        # From celestrak.com for May 14, 1994
        # 1994 05 14 49486  0.189443  0.306064 -0.1279402  0.0021743 -0.016163 -0.008660  0.000187  0.000039  28
        self.eops = EarthOrientationParameter(
            datetime.date(1994, 5, 14),
            0,
            0,
            -0.016163 * const.ARCSEC2RAD,
            -0.008660 * const.ARCSEC2RAD,
            0,
            0.0021743,
            28,
        )
        setEarthOrientationParameters(self.eops.date, self.eops)

    def testAzEl2RaDec(
        self,
    ):
        """Test converting AzEl to RaDec."""
        observer_ecef = lla2ecef(self.lla)
        radec = razel2radec(
            self.true_azel[0],
            self.true_azel[1],
            self.true_azel[2],
            self.true_azel[3],
            self.true_azel[4],
            self.true_azel[5],
            ecef2eci(observer_ecef, self.calendar_date),
            self.calendar_date,
        )

        azel = radec2razel(
            radec[0],
            radec[1],
            radec[2],
            radec[3],
            radec[4],
            radec[5],
            ecef2eci(observer_ecef, self.calendar_date),
            self.calendar_date,
        )

        assert np.allclose(
            np.asarray(azel),
            np.asarray(self.true_azel),
        )

        assert np.allclose(
            np.asarray(radec),
            np.asarray(self.true_radec_topo),
        )

    def testRaDec2AzEl(self):
        """Test converting RaDec to AzEl."""
        observer_ecef = lla2ecef(self.lla)
        azel = radec2razel(
            self.true_radec_topo[0],
            self.true_radec_topo[1],
            self.true_radec_topo[2],
            self.true_radec_topo[3],
            self.true_radec_topo[4],
            self.true_radec_topo[5],
            ecef2eci(observer_ecef, self.calendar_date),
            self.calendar_date,
        )

        radec = razel2radec(
            azel[0],
            azel[1],
            azel[2],
            azel[3],
            azel[4],
            azel[5],
            ecef2eci(observer_ecef, self.calendar_date),
            self.calendar_date,
        )

        assert np.allclose(
            np.asarray(azel),
            np.asarray(self.true_azel),
        )

        assert np.allclose(
            np.asarray(radec),
            np.asarray(self.true_radec_topo),
        )

    def testRazel(self):
        """Test converting ECI to AzEl."""
        assert np.allclose(
            eci2razel(
                self.eci,
                ecef2eci(lla2ecef(self.lla), self.calendar_date),
                self.calendar_date,
            ),
            self.true_azel,
        )

    def testAzEl2SEZ(self):
        """Test converting AzEl to SEZ state."""
        observer_ecef = lla2ecef(self.lla)
        tgt_ecef = observer_ecef + sez2ecef(
            razel2sez(
                self.true_azel[0],
                self.true_azel[1],
                self.true_azel[2],
                self.true_azel[3],
                self.true_azel[4],
                self.true_azel[5],
            ),
            self.lla[0],
            self.lla[1],
        )
        assert np.allclose(tgt_ecef, eci2ecef(self.eci, self.calendar_date))

    def testSEZ2ECI(self):
        """Test converting to ECI from SEZ."""
        observer_ecef = lla2ecef(self.lla)
        observer_eci = ecef2eci(observer_ecef, self.calendar_date)
        tgt_sez = getSlantRangeVector(observer_eci, self.eci, self.calendar_date)
        tgt_eci = observer_eci + sez2eci(tgt_sez, self.lla[0], self.lla[1], self.calendar_date)
        assert np.allclose(tgt_eci, self.eci)

    def testECI2SEZ(self):
        """Test converting to SEZ from ECI."""
        observer_ecef = lla2ecef(self.lla)
        observer_eci = ecef2eci(observer_ecef, self.calendar_date)
        slant_range_eci = self.eci - observer_eci
        tgt_sez = eci2sez(slant_range_eci, self.lla[0], self.lla[1], self.calendar_date)
        assert np.allclose(
            getSlantRangeVector(observer_eci, self.eci, self.calendar_date),
            tgt_sez,
        )

    def testTopocentricRaDec(self):
        """Test converting ECI to topocentric RaDec."""
        assert np.allclose(
            cartesian2spherical(self.eci - ecef2eci(lla2ecef(self.lla), self.calendar_date)),
            self.true_radec_topo,
        )

    def testGeocentricRaDec(self):
        """Test converting ECI to geocentric RaDec."""
        assert np.allclose(cartesian2spherical(self.eci), self.true_radec_geo)

    @pytest.mark.parametrize("spherical_coords", SPHERICAL_2_CARTESIAN)
    def testSpherical2Cartesian(self, spherical_coords):
        """Test conversion to and from spherical coordinates."""
        state = spherical2cartesian(*spherical_coords)
        rho_1, theta_1, phi_1, rho_dot_1, theta_dot_1, phi_dot_1 = cartesian2spherical(state)
        assert np.isclose(spherical_coords[0], rho_1)
        assert np.isclose(spherical_coords[1], theta_1)
        assert np.isclose(
            np.fmod(spherical_coords[2] + 2 * np.pi, 2 * np.pi),
            np.fmod(phi_1 + 2 * np.pi, 2 * np.pi),
        )
        assert np.isclose(spherical_coords[3], rho_dot_1)
        # In-determinant theta_dot
        if not np.isclose(np.sqrt(state[0] ** 2 + state[1] ** 2), 0):
            assert np.isclose(spherical_coords[4], theta_dot_1)
            assert np.isclose(spherical_coords[5], phi_dot_1)

    def testCartesianToSphericalEdgeCase(self):
        """Test conversion to spherical coordinates."""
        cartesian_coords = np.asarray([0, 0, 1000, -1, 2, -2])
        rho, theta, phi, rho_dot, theta_dot, phi_dot = cartesian2spherical(cartesian_coords)
        assert not np.isnan(rho)
        assert not np.isnan(theta)
        assert not np.isnan(phi)
        assert not np.isnan(rho_dot)
        assert theta_dot == 0
        assert phi_dot == 0
