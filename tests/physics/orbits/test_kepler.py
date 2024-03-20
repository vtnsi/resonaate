from __future__ import annotations

# Standard Library Imports
from typing import TYPE_CHECKING

# Third Party Imports
import pytest
from numpy import allclose, array, concatenate, cos, deg2rad, isclose, isfinite, rad2deg, sin, sqrt

# RESONAATE Imports
from resonaate.physics import constants as const
from resonaate.physics.bodies import Earth
from resonaate.physics.maths import _ATOL, rot1, rot3
from resonaate.physics.orbits.kepler import (
    KeplerProblemError,
    keplerSolveCOE,
    keplerSolveEQE,
    solveKeplerProblemUniversal,
)

# Local Imports
from . import POS_TEST_CASES, VEL_TEST_CASES

# Type Checking Imports
if TYPE_CHECKING:
    # Third Party Imports
    from numpy import ndarray

# ruff: noqa: N803, N806

E_PAR = 1.0
P_PAR = 25512.0
PAR_CASE = (P_PAR, E_PAR)
E_HYP = 5.0
P_HYP = -3189 * (1 - E_HYP**2)
HYP_CASE = (P_HYP, E_HYP)

# Various TOFs for each Vallado test case from his software
TOF: tuple[float] = (-300, -55, 0, 30, 100)
KEPLER_PROBLEM_CASES: tuple[float, ndarray, ndarray] = tuple(
    zip(TOF, POS_TEST_CASES, VEL_TEST_CASES),
)

# First case comes from Vallado Example 2-1, Others from Montenbruck Exercise 2-2
MEAN_ANOM_CASES: ndarray = deg2rad([235.4, 4, 50])
ECC_CASES: tuple[float] = (0.4, 0.72, 0.72)
ECC_ANOM_CASES: ndarray = deg2rad(
    [220.512074767522, rad2deg(0.24318719638), rad2deg(1.59249513093)],
)
KEPLER_EQN_TESTS: tuple[float] = tuple(zip(MEAN_ANOM_CASES, ECC_CASES, ECC_ANOM_CASES))

# Testing circular orbit cases
CIRCULAR_ANOM_CASES = (0, 90, 180, 360, -90, -270)


@pytest.mark.parametrize(("M", "ecc", "E"), KEPLER_EQN_TESTS)
def testKeplerCOE(M, ecc, E):
    """Test Kepler's equation accuracy using COE form."""
    E_0 = M - ecc if (0 > M > -const.PI or M > const.PI) else M + ecc
    assert isclose(E, keplerSolveCOE(E_0, M, ecc), rtol=0, atol=_ATOL)


@pytest.mark.parametrize("M", CIRCULAR_ANOM_CASES)
def testKeplerCOECircular(M):
    """Test Kepler's equation COE form for the circular orbit case."""
    ecc = 0.0
    E_0 = M - ecc if (0 > M > -const.PI or M > const.PI) else M + ecc
    assert isclose(M, keplerSolveCOE(E_0, M, ecc), rtol=0, atol=_ATOL)


@pytest.mark.parametrize(("M", "ecc", "E"), KEPLER_EQN_TESTS)
def testKeplerEQE(M, ecc, E):
    """Test Kepler's equation accuracy using EQE form."""
    raan = deg2rad(35)
    argp = deg2rad(182)
    h = ecc * sin(argp + raan)
    k = ecc * cos(argp + raan)
    lam = M + raan + argp
    assert isclose(E, keplerSolveEQE(lam, h, k, lam) - raan - argp, rtol=0, atol=_ATOL)


@pytest.mark.parametrize("M", CIRCULAR_ANOM_CASES)
def testKeplerEQECircular(M):
    """Test Kepler's equation EQE form for the circular orbit case."""
    ecc = 0.0
    raan = deg2rad(35)
    argp = deg2rad(182)
    h = ecc * sin(argp + raan)
    k = ecc * cos(argp + raan)
    lam = M + raan + argp
    assert isclose(M, keplerSolveEQE(lam, h, k, lam) - raan - argp, rtol=0, atol=_ATOL)


def testKeplerProblemAccuracy():
    """Test the accuracy of Kepler's problem using Example 2-4 from Vallado."""
    init_eci = [1131.340, -2282.343, 6672.423, -5.64305, 4.30333, 2.42879]
    final_eci = [-4219.7527, 4363.0292, -3958.7666, 3.689866, -1.916735, -6.112511]
    tof = 40 * 60
    # forwards
    assert allclose(final_eci, solveKeplerProblemUniversal(init_eci, tof), rtol=1e-6)
    # backwards
    assert allclose(init_eci, solveKeplerProblemUniversal(final_eci, -tof), rtol=1e-6)


@pytest.mark.parametrize("tof", TOF)
@pytest.mark.parametrize(("pos", "vel"), tuple(zip(POS_TEST_CASES, VEL_TEST_CASES)))
def testKeplerProblemCases(tof, pos, vel):
    """Test Kepler's problem forwards and then backwards is consistent."""
    init_eci = concatenate((pos, vel), axis=0)
    final_eci = solveKeplerProblemUniversal(init_eci, tof * 60, tol=1e-12)
    assert allclose(init_eci, solveKeplerProblemUniversal(final_eci, -tof * 60, tol=1e-12))


@pytest.mark.parametrize(("p", "e"), [PAR_CASE, HYP_CASE])
def testKeplerProblemParabolicHyperbolic(p, e):
    """Test Kepler's problem raises error for parabolic case."""
    tof = 3600
    inc = deg2rad(55.0)
    raan = deg2rad(10.0)
    argp = deg2rad(75.0)
    nu = deg2rad(45.0)

    init_eci = _coe2rv(p, e, inc, raan, argp, nu)
    final_eci = solveKeplerProblemUniversal(init_eci, tof)
    assert all(isfinite(final_eci))


def testKeplerProblemBadValues():
    """Test Kepler's problem raises error for parabolic case."""
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
    # Save cos(), sin() of anomaly angle, semiparameter rectum
    cos_anom, sin_anom = cos(true_anom), sin(true_anom)

    # Define PQW position, velocity vectors
    r_pqw = p / (1.0 + ecc * cos_anom) * array([cos_anom, sin_anom, 0.0])
    v_pqw = sqrt(Earth.mu / p) * array([-sin_anom, ecc + cos_anom, 0.0])

    # Define rotation matrix from PQW to ECI
    rot_pqw2eci = rot3(-raan).dot(rot1(-inc).dot(rot3(-argp)))

    return concatenate([rot_pqw2eci.dot(r_pqw), rot_pqw2eci.dot(v_pqw)], axis=0)
