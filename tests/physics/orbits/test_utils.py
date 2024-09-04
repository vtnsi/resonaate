from __future__ import annotations

# Standard Library Imports
from typing import TYPE_CHECKING

# Third Party Imports
import pytest
from numpy import allclose, array, cos, deg2rad, fabs, isclose, sin, sqrt, tan
from scipy.linalg import norm

# RESONAATE Imports
from resonaate.physics.constants import TWOPI
from resonaate.physics.orbits import EccentricityError, InclinationError
from resonaate.physics.orbits.anomaly import meanLong2EccLong
from resonaate.physics.orbits.utils import (
    getAngularMomentum,
    getAngularMomentumFromEQE,
    getArgumentLatitude,
    getArgumentPerigee,
    getEccentricity,
    getEccentricityFromEQE,
    getEquinoctialBasisVectors,
    getFlightPathAngle,
    getInclinationFromEQE,
    getLineOfNodes,
    getMeanMotion,
    getOrbitalEnergy,
    getPeriod,
    getRightAscension,
    getSemiMajorAxis,
    getSmaFromMeanMotion,
    getTrueAnomaly,
    getTrueLongitude,
    getTrueLongitudePeriapsis,
    retrogradeFactor,
    singularityCheck,
    universalC2C3,
)

# Local Imports
from . import INCLINATIONS, VALLADO_AAS_COE, VALLADO_AAS_EQE, VALLADO_AAS_RV

# Type Checking Imports
if TYPE_CHECKING:
    # Third Party Imports
    from numpy import ndarray

# ruff: noqa: N803, N806

PSI: tuple[float] = (-1e-8, 0, 1e-8, 6.150035, -6.174583)

IS_RETRO: tuple[bool] = (1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, -1, -1)

ECC: tuple[float] = [0, 0, 0.0001, 0.0001]
INC: ndarray = deg2rad([0, 10, 0, 10])
SINGULAR_COE: ndarray = deg2rad([60, 70, 250])
ADJUSTED_COE: list[ndarray] = [
    deg2rad([0, 0, 20]),
    deg2rad([60, 0, 320]),
    deg2rad([0, 130, 250]),
    deg2rad([60, 70, 250]),
]

RV_SET: list[ndarray] = [
    array([1131.340, -2282.343, 6672.423, -5.64305, 4.30333, 2.42879]),
    array([6524.834, 6862.875, 6448.296, 4.901327, 5.533756, -1.976341]),
]
SMA: list[float] = [7200.4706, 36127.343]
ENERGY: list[float] = [-27.678777, -5.516604]


@pytest.mark.parametrize("psi", PSI)
def testUniversalC2C3(psi: float):
    """Test edge case values of Stumpff coeff calculations."""
    c2, c3 = universalC2C3(psi)
    if fabs(psi) <= 1e-6:
        assert c2 == 0.5
        assert c3 == 1.0 / 6.0
    else:
        assert c2 != 0.5
        assert c3 != 1.0 / 6.0


@pytest.mark.parametrize(("is_retro", "inc"), tuple(zip(IS_RETRO, INCLINATIONS[:-2])))
def testRetrogradeFactor(is_retro: int, inc: float):
    """Test retrograde factor calculation."""
    assert is_retro == retrogradeFactor(inc)


@pytest.mark.parametrize(("ecc", "inc", "adjusted"), tuple(zip(ECC, INC, ADJUSTED_COE)))
def testSingularityCheck(ecc: float, inc: float, adjusted: ndarray):
    """Test COE singularity check for adjusting singular angles."""
    assert allclose(adjusted, singularityCheck(ecc, inc, *SINGULAR_COE), rtol=1e-12, atol=1e-12)


@pytest.mark.parametrize(("eci", "sma"), tuple(zip(RV_SET, SMA)))
def testGetSMA(eci: ndarray, sma: float):
    """Test calculating SMA from ECI pos, vel."""
    assert isclose(getSemiMajorAxis(norm(eci[:3]), norm(eci[3:])), sma)


@pytest.mark.parametrize(("eci", "energy"), tuple(zip(RV_SET, ENERGY)))
def testGetEnergy(eci: ndarray, energy: float):
    """Test calculating energy from ECI pos, vel."""
    assert isclose(getOrbitalEnergy(norm(eci[:3]), norm(eci[3:])), energy)


def testgetMeanMotion():
    """Test calculating mean motion from SMA."""
    assert isclose(getMeanMotion(42164.1696), TWOPI / 86164.0905)


def testgetSmaFromMeanMotion():
    """Tests calculating the SMA from mean motion."""
    m = getMeanMotion(42164.1696)
    assert isclose(42164.1696, getSmaFromMeanMotion(m))


def testGetPeriod():
    """Test calculating Period from SMA."""
    assert isclose(getPeriod(42164.1696), 86164.0905)


@pytest.mark.parametrize("eci", RV_SET[1:])
def testGetEccentricity(eci: ndarray):
    """Test calculating ecc from ECI pos, vel."""
    e_vec = array([-0.3146, -0.38523, 0.66804])
    e = 0.832853
    ecc, ecc_vec = getEccentricity(eci[:3], eci[3:])
    assert isclose(ecc, e)
    # [NOTE]: test case is _not_ normalized
    assert allclose(ecc_vec * ecc, e_vec)


def testGetLineOfNodes():
    """Test calculating line of nodes vector from angular momentum."""
    h_vec = array([-49246.7, 44500.5, 2469.6])
    n_vec = array([-44500.5, -49246.7, 0.0])
    assert allclose(getLineOfNodes(h_vec), n_vec)


@pytest.mark.parametrize("eci", RV_SET[1:])
def testGetAngMomentum(eci: ndarray):
    """Test calculating angular momentum from ECI pos, vel."""
    h_vec = array([-49246.7, 44500.5, 2469.6])
    assert allclose(getAngularMomentum(eci[:3], eci[3:]), h_vec, rtol=0, atol=5e-2)


@pytest.mark.parametrize("eci", RV_SET[1:])
def testGetTrueLongitude(eci: ndarray):
    """Test calculating true longitude from ECI pos."""
    lambda_true = deg2rad(55.282587)
    assert allclose(getTrueLongitude(eci[:3]), lambda_true)


@pytest.mark.parametrize("eci", RV_SET[1:])
def testGetArgLat(eci: ndarray):
    """Test calculating argument of latitude from ECI pos & line of nodes vector."""
    n_vec = array([-44500.5, -49246.7, 0.0])
    n_vec = n_vec / norm(n_vec)
    arg_lat_true = deg2rad(145.60549)
    assert allclose(getArgumentLatitude(eci[:3], n_vec), arg_lat_true, rtol=0, atol=5e-3)


@pytest.mark.parametrize("eci", RV_SET[1:])
def testGetTrueLongPer(eci: ndarray):
    """Test calculating true long of periapsis from ecc vector."""
    omega_true = deg2rad(247.806)
    _, ecc_vec = getEccentricity(eci[:3], eci[3:])
    assert allclose(getTrueLongitudePeriapsis(ecc_vec), omega_true)


def testgetRightAscension():
    """Test calculating RAAN from line of nodes vector."""
    n_vec = array([-44500.5, -49246.7, 0.0])
    n_vec = n_vec / norm(n_vec)
    raan = deg2rad(227.898)
    assert allclose(getRightAscension(n_vec), raan)


@pytest.mark.parametrize("eci", RV_SET[1:])
def testGetArgumentPerigee(eci: ndarray):
    """Test calculating ARGP from line of nodes & ecc vectors."""
    n_vec = array([-44500.5, -49246.7, 0.0])
    n_vec = n_vec / norm(n_vec)
    _, e_vec = getEccentricity(eci[:3], eci[3:])
    argp = deg2rad(53.38)
    assert allclose(getArgumentPerigee(e_vec, n_vec), argp, rtol=0, atol=1e-4)


@pytest.mark.parametrize("eci", RV_SET[1:])
def testgetTrueAnomaly(eci: ndarray):
    """Test calculating true anomaly from ECI pos & vel."""
    n_vec = array([-44500.5, -49246.7, 0.0])
    n_vec = n_vec / norm(n_vec)
    _, e_vec = getEccentricity(eci[:3], eci[3:])
    t_anom = deg2rad(92.335)
    assert allclose(getTrueAnomaly(eci[:3], eci[3:], e_vec), t_anom)


def testGetIncFromEQE():
    """Test calculating inc from p & q."""
    p = VALLADO_AAS_EQE[3]
    q = VALLADO_AAS_EQE[4]
    assert allclose(getInclinationFromEQE(p, q, retro=True), VALLADO_AAS_COE[2])


def testGetIncFromEQEBadVal():
    """Test bad inclination value."""
    # Equal to 180 deg, but retro=False
    inc = deg2rad(180)
    with pytest.raises(InclinationError):
        getInclinationFromEQE(0, tan(inc / 2), retro=False)
    # Above inc limit, but retro=False
    inc = deg2rad(180 - 0.99e-7)
    with pytest.raises(InclinationError):
        getInclinationFromEQE(0, tan(inc / 2), retro=False)


def testGetEccFromEQE():
    """Test calculating ecc from h & k."""
    h = VALLADO_AAS_EQE[1]
    k = VALLADO_AAS_EQE[2]
    assert allclose(getEccentricityFromEQE(h, k), VALLADO_AAS_COE[1])


def testGetEccFromEQEBadVal():
    """Test bad eccentricity value."""
    # Parabolic
    with pytest.raises(EccentricityError):
        getEccentricityFromEQE(sqrt(0.5), sqrt(0.5))
    # Hyperbolic
    with pytest.raises(EccentricityError):
        getEccentricityFromEQE(sqrt(1), sqrt(1))


def testGetBasisEQE():
    """Test calculating EQE basis vectors from p & q."""
    a = VALLADO_AAS_EQE[0]
    p, q = VALLADO_AAS_EQE[3], VALLADO_AAS_EQE[4]
    h, k = VALLADO_AAS_EQE[1], VALLADO_AAS_EQE[2]
    lam = VALLADO_AAS_EQE[5]

    F = meanLong2EccLong(lam, h, k)
    f, g = getEquinoctialBasisVectors(p, q, retro=True)

    # Minus RAAN b/c retrograde
    L = VALLADO_AAS_COE[5] - VALLADO_AAS_COE[3] + VALLADO_AAS_COE[4]
    r = a * (1 - h * sin(F) - k * cos(F))
    X, Y = r * cos(L), r * sin(L)

    test_pos = f * X + g * Y
    assert allclose(VALLADO_AAS_RV[:3], test_pos)


def testGetAngMomFromEQE():
    """Test calculating angular momentum from p & q."""
    h_vec = getAngularMomentum(VALLADO_AAS_RV[:3], VALLADO_AAS_RV[3:])
    h_vec = h_vec / norm(h_vec)
    p = VALLADO_AAS_EQE[3]
    q = VALLADO_AAS_EQE[4]
    assert allclose(getAngularMomentumFromEQE(p, q, retro=True), h_vec)


def testGetFlightPathAngle():
    """Test calculating fpa from ecc and anomaly."""
    fpa = getFlightPathAngle(VALLADO_AAS_COE[1], VALLADO_AAS_COE[5])
    # Vallado AAS paper case
    assert allclose(fpa, deg2rad(0.0553210))
    # Circular orbit case
    assert getFlightPathAngle(0.0, 3.0) == 0.0
