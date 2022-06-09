# pylint: disable=attribute-defined-outside-init, no-self-use
# Standard Library Imports
# Third Party Imports
import pytest
from numpy import isclose, deg2rad, cos, sin, allclose, concatenate, rad2deg, sqrt, array, isfinite
# RESONAATE Imports
try:
    from resonaate.physics.orbits.kepler import (
        solveKeplerProblemUniversal, keplerSolveCOE, keplerSolveEQE, KeplerProblemError
    )
    from resonaate.physics.math import _ATOL, rot1, rot3
    from resonaate.physics.bodies import Earth
    from resonaate.physics import constants as const
except ImportError as error:
    raise Exception(
        f"Please ensure you have appropriate packages installed:\n {error}"
    ) from error
# Testing Imports
from .conftest import POS_TEST_CASES, VEL_TEST_CASES
from ...conftest import BaseTestCase


E_PAR = 1.0
P_PAR = 25512.0
PAR_CASE = (P_PAR, E_PAR)
E_HYP = 5.0
P_HYP = -3189 * (1 - E_HYP**2)
HYP_CASE = (P_HYP, E_HYP)


class TestKepler(BaseTestCase):
    """Test pure functions that convert to/from orbital element sets."""

    # Various TOFs for each Vallado test case from his software
    TOF = (-300, -55, 0, 30, 100)
    KEPLER_PROBLEM_CASES = tuple(zip(TOF, POS_TEST_CASES, VEL_TEST_CASES))

    # First case comes from Vallado Example 2-1, Others from Montenbruck Exercise 2-2
    MEAN_ANOM_CASES = deg2rad([235.4, 4, 50])
    ECC_CASES = (0.4, 0.72)
    ECC_ANOM_CASES = deg2rad([220.512074767522, rad2deg(0.24318719638), rad2deg(1.59249513093)])
    KEPLER_EQN_TESTS = tuple(zip(MEAN_ANOM_CASES, ECC_CASES, ECC_ANOM_CASES))

    # Testing circular orbit cases
    CIRCULAR_ANOM_CASES = (0, 90, 180, 360, -90, -270)

    @pytest.mark.parametrize("M, ecc, E", KEPLER_EQN_TESTS)
    def testKeplerCOE(self, M, ecc, E):
        """Test Kepler's equation accuracy using COE form."""
        # pylint: disable=invalid-name
        if 0 > M > -const.PI or M > const.PI:
            E_0 = M - ecc
        else:
            E_0 = M + ecc
        assert isclose(E, keplerSolveCOE(E_0, M, ecc), rtol=0, atol=_ATOL)

    @pytest.mark.parametrize("M", CIRCULAR_ANOM_CASES)
    def testKeplerCOECircular(self, M):
        """Test Kepler's equation COE form for the circular orbit case."""
        # pylint: disable=invalid-name
        ecc = 0.0
        if 0 > M > -const.PI or M > const.PI:
            E_0 = M - ecc
        else:
            E_0 = M + ecc
        assert isclose(M, keplerSolveCOE(E_0, M, ecc), rtol=0, atol=_ATOL)

    @pytest.mark.parametrize("M, ecc, E", KEPLER_EQN_TESTS)
    def testKeplerEQE(self, M, ecc, E):
        """Test Kepler's equation accuracy using EQE form."""
        # pylint: disable=invalid-name
        raan = deg2rad(35)
        argp = deg2rad(182)
        h = ecc * sin(argp + raan)
        k = ecc * cos(argp + raan)
        lam = M + raan + argp
        assert isclose(E, keplerSolveEQE(lam, h, k, lam) - raan - argp, rtol=0, atol=_ATOL)

    @pytest.mark.parametrize("M", CIRCULAR_ANOM_CASES)
    def testKeplerEQECircular(self, M):
        """Test Kepler's equation EQE form for the circular orbit case."""
        # pylint: disable=invalid-name
        ecc = 0.0
        raan = deg2rad(35)
        argp = deg2rad(182)
        h = ecc * sin(argp + raan)
        k = ecc * cos(argp + raan)
        lam = M + raan + argp
        assert isclose(M, keplerSolveEQE(lam, h, k, lam) - raan - argp, rtol=0, atol=_ATOL)

    def testKeplerProblemAcccuracy(self):
        """Test the accuracy of Kepler's problem using Example 2-4 from Vallado."""
        # pylint: disable=invalid-name
        init_eci = [1131.340, -2282.343, 6672.423, -5.64305, 4.30333, 2.42879]
        final_eci = [-4219.7527, 4363.0292, -3958.7666, 3.689866, -1.916735, -6.112511]
        tof = 40 * 60
        # forwards
        assert allclose(final_eci, solveKeplerProblemUniversal(init_eci, tof), rtol=1e-6)
        # backwards
        assert allclose(init_eci, solveKeplerProblemUniversal(final_eci, -tof), rtol=1e-6)

    @pytest.mark.parametrize("tof", TOF)
    @pytest.mark.parametrize("pos, vel", tuple(zip(POS_TEST_CASES, VEL_TEST_CASES)))
    def testKeplerProblemCases(self, tof, pos, vel):
        """Test Kepler's problem forwards and then backwards is consistent."""
        # pylint: disable=invalid-name
        init_eci = concatenate((pos, vel), axis=0)
        final_eci = solveKeplerProblemUniversal(init_eci, tof * 60, tol=1e-12)
        assert allclose(init_eci, solveKeplerProblemUniversal(final_eci, -tof * 60, tol=1e-12))

    @pytest.mark.parametrize("p, e", (PAR_CASE, HYP_CASE))
    def testKeplerProblemParabolichyperbolic(self, p, e):
        """Test Kepler's problem raises error for parabolic case."""
        # pylint: disable=invalid-name
        tof = 3600
        inc = deg2rad(55.0)
        raan = deg2rad(10.0)
        argp = deg2rad(75.0)
        nu = deg2rad(45.0)

        init_eci = _coe2rv(p, e, inc, raan, argp, nu)
        final_eci = solveKeplerProblemUniversal(init_eci, tof)
        assert all(isfinite(final_eci))

    def testKeplerProblemBadValues(self):
        """Test Kepler's problem raises error for parabolic case."""
        # pylint: disable=invalid-name
        tof = 3600
        pos = POS_TEST_CASES[0]
        vel = VEL_TEST_CASES[0]

        init_eci = concatenate([pos, vel])
        with pytest.raises(KeplerProblemError):
            solveKeplerProblemUniversal(init_eci, tof, maxiter=1)

        with pytest.raises(KeplerProblemError):
            solveKeplerProblemUniversal(init_eci, tof, maxiter=5, tol=1e-3)


def _coe2rv(p, ecc, inc, raan, argp, true_anom):
    """Convert a set of COEs to an ECI (J2000) position and velocity vector."""
    # pylint: disable=invalid-name
    # Save cos(), sin() of anomaly angle, semiparameter rectum
    cos_anom, sin_anom = cos(true_anom), sin(true_anom)

    # Define PQW position, velocity vectors
    r_pqw = p / (1.0 + ecc * cos_anom) * array([cos_anom, sin_anom, 0.0])
    v_pqw = sqrt(Earth.mu / p) * array([-sin_anom, ecc + cos_anom, 0.0])

    # Define rotation matrix from PQW to ECI
    rot_pqw2eci = rot3(-raan).dot(rot1(-inc).dot(rot3(-argp)))

    return concatenate([rot_pqw2eci.dot(r_pqw), rot_pqw2eci.dot(v_pqw)], axis=0)
