# pylint: disable=attribute-defined-outside-init, no-self-use
# Standard Library Imports
# Third Party Imports
import pytest
from numpy import deg2rad, linspace
# RESONAATE Imports
try:
    import resonaate.physics.constants as const
    from resonaate.physics.orbits import (
        isInclined, isEccentric, check_ecc, fixAngleQuadrant, wrap_anomaly, InclinationError, EccentricityError
    )
    from resonaate.physics.math import wrapAngle2Pi
except ImportError as error:
    raise Exception(
        f"Please ensure you have appropriate packages installed:\n {error}"
    ) from error
# Testing Imports
from .conftest import INCLINCATIONS, INCLINED, ECCENTRICITIES, ECCENTRIC


INCLINED_TEST = tuple(zip(INCLINCATIONS, INCLINED))
ECCENTRIC_TEST = tuple(zip(ECCENTRICITIES, ECCENTRIC))


@pytest.mark.parametrize("angle, is_inclined", INCLINED_TEST)
def testIsInclined(angle, is_inclined):
    """Test isInclined function for bad/good values."""
    if is_inclined is not None:
        assert isInclined(angle) == is_inclined
    else:
        with pytest.raises(InclinationError):
            isInclined(angle)


@pytest.mark.parametrize("ecc, is_eccentric", ECCENTRIC_TEST)
def testIsEccentric(ecc, is_eccentric):
    """Test isInclined function for bad/good values."""
    if is_eccentric is not None:
        assert isEccentric(ecc) == is_eccentric
    else:
        with pytest.raises(EccentricityError):
            isEccentric(ecc)


def _dummyAnomCheckFunc(angle, ecc):
    return angle - ecc


def _dummyAnomFunc(angle):
    return angle + 1


wrappedEccCheck = check_ecc(_dummyAnomCheckFunc)
wrappedAnomWrap = wrap_anomaly(_dummyAnomFunc)


QUAD_CHECK_TEST = list(zip(
    deg2rad([
        0, 5, 175, 180, 185, 355, 360, 365,
        0, 5, 175, 180, 185, 355, 360, 365,
        0, 5, 175, 180, 185, 355, 360, 365,
    ]),
    [
        -1, -1, -1, -1, -1, -1, -1, -1,
        1, 1, 1, 1, 1, 1, 1, 1,
        0, 0, 0, 0, 0, 0, 0, 0,
    ],
))

ECC_CHECK_TEST = list(zip(
    deg2rad([
        0, 5, 175, 180, 185, 355, 360, 365,
        0, 5, 175, 180, 185, 355, 360, 365,
    ]),
    [
        0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1,
        0, 0, 0, 0, 0, 0, 0, 0,
    ],
))

ANOM_WRAP_TEST = linspace(-5, 5, 21) * const.PI


@pytest.mark.parametrize("angle, check", QUAD_CHECK_TEST)
def testQuadCheckDecorator(angle, check):
    """Test quadarant check function."""
    if check >= 0:
        assert fixAngleQuadrant(angle, check) == angle
    else:
        assert fixAngleQuadrant(angle, check) == const.TWOPI - angle


@pytest.mark.parametrize("anom, ecc", ECC_CHECK_TEST)
def testEccCheckDecorator(anom, ecc):
    """Test eccentricity check decorator function."""
    if isEccentric(ecc) >= 0:
        assert wrappedEccCheck(anom, ecc) == anom - ecc
    else:
        assert wrappedEccCheck(anom, ecc) == anom


@pytest.mark.parametrize("angle", ANOM_WRAP_TEST)
def testAnomWrapDecorator(angle):
    """Test anomaly wrap decorator function."""
    assert wrappedAnomWrap(angle) == wrapAngle2Pi(angle + 1)
