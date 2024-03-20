from __future__ import annotations

# Standard Library Imports
from typing import TYPE_CHECKING

# Third Party Imports
import pytest
from numpy import deg2rad, linspace

# RESONAATE Imports
import resonaate.physics.constants as const
from resonaate.physics.maths import wrapAngle2Pi
from resonaate.physics.orbits import (
    EccentricityError,
    InclinationError,
    check_ecc,
    fixAngleQuadrant,
    isEccentric,
    isInclined,
    wrap_anomaly,
)

# Local Imports
from . import ECCENTRIC, ECCENTRICITIES, INCLINATIONS, INCLINED

# Type Checking Imports
if TYPE_CHECKING:
    # Standard Library Imports
    from collections.abc import Callable

    # Third Party Imports
    from numpy import ndarray

INCLINED_TEST: tuple[tuple[float, bool]] = tuple(zip(INCLINATIONS, INCLINED))
ECCENTRIC_TEST: tuple[tuple[float, bool]] = tuple(zip(ECCENTRICITIES, ECCENTRIC))


@pytest.mark.parametrize(("angle", "is_inclined"), INCLINED_TEST)
def testIsInclined(angle: float, is_inclined: bool):
    """Test isInclined function for bad/good values."""
    if is_inclined is not None:
        assert isInclined(angle) == is_inclined
    else:
        with pytest.raises(InclinationError):
            isInclined(angle)


@pytest.mark.parametrize(("ecc", "is_eccentric"), ECCENTRIC_TEST)
def testIsEccentric(ecc: float, is_eccentric: bool):
    """Test isInclined function for bad/good values."""
    if is_eccentric is not None:
        assert isEccentric(ecc) == is_eccentric
    else:
        with pytest.raises(EccentricityError):
            isEccentric(ecc)


def _dummyAnomCheckFunc(angle: float, ecc: float) -> float:
    return angle - ecc


def _dummyAnomFunc(angle: float) -> float:
    return angle + 1


wrapped_ecc_check: Callable[..., float] = check_ecc(_dummyAnomCheckFunc)
wrapped_anom_wrap: Callable[..., float] = wrap_anomaly(_dummyAnomFunc)


QUAD_CHECK_TEST: list[tuple[float, float]] = list(
    zip(
        deg2rad(
            [
                0,
                5,
                175,
                180,
                185,
                355,
                360,
                365,
                0,
                5,
                175,
                180,
                185,
                355,
                360,
                365,
                0,
                5,
                175,
                180,
                185,
                355,
                360,
                365,
            ],
        ),
        [
            -1,
            -1,
            -1,
            -1,
            -1,
            -1,
            -1,
            -1,
            1,
            1,
            1,
            1,
            1,
            1,
            1,
            1,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
        ],
    ),
)

ECC_CHECK_TEST: list[tuple[float, float]] = list(
    zip(
        deg2rad(
            [
                0,
                5,
                175,
                180,
                185,
                355,
                360,
                365,
                0,
                5,
                175,
                180,
                185,
                355,
                360,
                365,
            ],
        ),
        [
            0.1,
            0.1,
            0.1,
            0.1,
            0.1,
            0.1,
            0.1,
            0.1,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
        ],
    ),
)

ANOM_WRAP_TEST: ndarray = linspace(-5, 5, 21) * const.PI


@pytest.mark.parametrize(("angle", "check"), QUAD_CHECK_TEST)
def testQuadCheckDecorator(angle: float, check: float):
    """Test quadrant check function."""
    if check >= 0:
        assert fixAngleQuadrant(angle, check) == angle
    else:
        assert fixAngleQuadrant(angle, check) == const.TWOPI - angle


@pytest.mark.parametrize(("anom", "ecc"), ECC_CHECK_TEST)
def testEccCheckDecorator(anom: float, ecc: float):
    """Test eccentricity check decorator function."""
    if isEccentric(ecc) >= 0:
        assert wrapped_ecc_check(anom, ecc) == anom - ecc
    else:
        assert wrapped_ecc_check(anom, ecc) == anom


@pytest.mark.parametrize("angle", ANOM_WRAP_TEST)
def testAnomWrapDecorator(angle: float):
    """Test anomaly wrap decorator function."""
    assert wrapped_anom_wrap(angle) == wrapAngle2Pi(angle + 1)
