from __future__ import annotations

# Standard Library Imports
from typing import TYPE_CHECKING

# Third Party Imports
import pytest
from numpy import cos, deg2rad, isclose, rad2deg, sin

# RESONAATE Imports
from resonaate.physics.maths import _ATOL, wrapAngle2Pi
from resonaate.physics.orbits.anomaly import (
    eccAnom2MeanAnom,
    eccAnom2TrueAnom,
    eccLong2MeanLong,
    meanAnom2EccAnom,
    meanAnom2TrueAnom,
    meanLong2EccLong,
    meanLong2TrueAnom,
    trueAnom2EccAnom,
    trueAnom2MeanAnom,
    trueAnom2MeanLong,
)

# Local Imports
from . import VALLADO_AAS_COE, VALLADO_AAS_EQE, H, K

# Type Checking Imports
if TYPE_CHECKING:
    # Third Party Imports
    from numpy import ndarray

# ruff: noqa: N803, N806

MEAN_ANOM: float = deg2rad(65.10238)
TRUE_LONG: float = deg2rad(69.5264380)

# Test short circuit for circular EQE anomalies
IS_ECC: tuple[bool] = (False, True, True, True)
EQE_ANOM_ECC: tuple[tuple[float, float, bool]] = tuple(zip(H, K, IS_ECC))

# First case comes from Vallado Example 2-1, Others from Montenbruck Exercise 2-2
MEAN_ANOM_CASES: ndarray = deg2rad([235.4, 4, 50])
ECC_CASES: tuple[float] = (0.4, 0.72, 0.72)
ECC_ANOM_CASES: ndarray = deg2rad(
    [220.512074767522, rad2deg(0.24318719638), rad2deg(1.59249513093)],
)
ANOM_TESTS: tuple[tuple[float, float, float]] = tuple(
    zip(MEAN_ANOM_CASES, ECC_CASES, ECC_ANOM_CASES),
)


@pytest.mark.parametrize("anom", deg2rad([0, 1, 2, 5]))
@pytest.mark.parametrize(("h", "k", "is_ecc"), EQE_ANOM_ECC)
def testEQECircularCase(anom: float, h: float, k: float, is_ecc: bool):
    """Test calculating true long of periapsis from ecc vector."""
    if is_ecc:
        assert eccLong2MeanLong(anom, h, k) != anom
        assert meanLong2EccLong(anom, h, k) != anom
    else:
        assert eccLong2MeanLong(anom, h, k) == anom
        assert meanLong2EccLong(anom, h, k) == anom


@pytest.mark.parametrize(("M", "ecc", "E"), ANOM_TESTS)
def testMeanLong2EccLong(M: float, ecc: float, E: float):
    """Test anomaly conversion using Kepler's equation."""
    raan = deg2rad(35)
    argp = deg2rad(182)
    h = ecc * sin(argp + raan)
    k = ecc * cos(argp + raan)
    lam = M + raan + argp
    F = wrapAngle2Pi(E + raan + argp)
    assert isclose(F, meanLong2EccLong(lam, h, k), rtol=0, atol=_ATOL)


@pytest.mark.parametrize(("M", "ecc", "E"), ANOM_TESTS)
def testEccLong2MeanLong(M: float, ecc: float, E: float):
    """Test anomaly conversion using Kepler's equation."""
    raan = deg2rad(35)
    argp = deg2rad(182)
    h = ecc * sin(argp + raan)
    k = ecc * cos(argp + raan)
    lam = wrapAngle2Pi(M + raan + argp)
    F = E + raan + argp
    assert isclose(lam, eccLong2MeanLong(F, h, k), rtol=0, atol=_ATOL)


@pytest.mark.parametrize(("M", "ecc", "E"), ANOM_TESTS)
def testMeanAnom2EccAnom(M: float, ecc: float, E: float):
    """Test anomaly conversion using Kepler's equation."""
    assert isclose(E, meanAnom2EccAnom(M, ecc), rtol=0, atol=_ATOL)


@pytest.mark.parametrize(("M", "ecc", "E"), ANOM_TESTS)
def testEccAnom2MeanAnom(M: float, ecc: float, E: float):
    """Test anomaly conversion."""
    assert isclose(M, eccAnom2MeanAnom(E, ecc), rtol=0, atol=_ATOL)


def testTrueAnom2EccAnom():
    """Test anomaly conversion."""
    nu = VALLADO_AAS_COE[5]
    e = VALLADO_AAS_COE[1]
    E = meanAnom2EccAnom(MEAN_ANOM, e)
    assert isclose(trueAnom2EccAnom(nu, e), E, rtol=0, atol=2e-7)


def testEccAnom2TrueAnom():
    """Test anomaly conversion."""
    nu = VALLADO_AAS_COE[5]
    e = VALLADO_AAS_COE[1]
    E = meanAnom2EccAnom(MEAN_ANOM, e)
    assert isclose(eccAnom2TrueAnom(E, e), nu, rtol=0, atol=2e-7)


def testTrueAnom2MeanAnom():
    """Test anomaly conversion."""
    nu = VALLADO_AAS_COE[5]
    e = VALLADO_AAS_COE[1]
    assert isclose(trueAnom2MeanAnom(nu, e), MEAN_ANOM, rtol=0, atol=2e-7)


def testMeanAnom2TrueAnom():
    """Test anomaly conversion."""
    nu = VALLADO_AAS_COE[5]
    e = VALLADO_AAS_COE[1]
    assert isclose(meanAnom2TrueAnom(MEAN_ANOM, e), nu, rtol=0, atol=2e-7)


def testTrueAnom2MeanLong():
    """Test anomaly conversion."""
    nu = VALLADO_AAS_COE[5]
    e = VALLADO_AAS_COE[1]
    raan = VALLADO_AAS_COE[3]
    argp = VALLADO_AAS_COE[4]
    lam = VALLADO_AAS_EQE[5]
    assert isclose(trueAnom2MeanLong(nu, e, raan, argp, retro=True), lam, rtol=0, atol=2e-7)


def testMeanLong2TrueAnom():
    """Test anomaly conversion."""
    nu = VALLADO_AAS_COE[5]
    e = VALLADO_AAS_COE[1]
    raan = VALLADO_AAS_COE[3]
    argp = VALLADO_AAS_COE[4]
    lam = VALLADO_AAS_EQE[5]
    assert isclose(meanLong2TrueAnom(lam, e, raan, argp, retro=True), nu, rtol=0, atol=2e-7)
