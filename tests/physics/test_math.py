from __future__ import annotations

# Standard Library Imports
from typing import TYPE_CHECKING

# Third Party Imports
import pytest
from numpy import (
    allclose,
    array,
    deg2rad,
    degrees,
    isclose,
    linspace,
    ones_like,
    radians,
    zeros_like,
)

# RESONAATE Imports
from resonaate.physics.constants import PI, TWOPI
from resonaate.physics.maths import (
    ShapeError,
    angularMean,
    residual,
    residuals,
    wrapAngle2Pi,
    wrapAngleNegPiPi,
)

# Type Checking Imports
if TYPE_CHECKING:
    # Third Party Imports
    from numpy import ndarray

UNWRAPPED_ANGLES: ndarray = linspace(-5, 5, 41) * PI


WRAPPED_NEG_PI: ndarray = (
    array(
        [
            1.0,
            -0.75,
            -0.5,
            -0.25,
            0.0,
            0.25,
            0.5,
            0.75,
            1.0,
            -0.75,
            -0.5,
            -0.25,
            0.0,
            0.25,
            0.5,
            0.75,
            1.0,
            -0.75,
            -0.5,
            -0.25,
            0.0,
            0.25,
            0.5,
            0.75,
            1.0,
            -0.75,
            -0.5,
            -0.25,
            0.0,
            0.25,
            0.5,
            0.75,
            1.0,
            -0.75,
            -0.5,
            -0.25,
            0.0,
            0.25,
            0.5,
            0.75,
            1.0,
        ],
    )
    * PI
)


WRAPPED_TWO_PI: ndarray = (
    array(
        [
            1.0,
            1.25,
            1.5,
            1.75,
            0.0,
            0.25,
            0.5,
            0.75,
            1.0,
            1.25,
            1.5,
            1.75,
            0.0,
            0.25,
            0.5,
            0.75,
            1.0,
            1.25,
            1.5,
            1.75,
            0.0,
            0.25,
            0.5,
            0.75,
            1.0,
            1.25,
            1.5,
            1.75,
            0.0,
            0.25,
            0.5,
            0.75,
            1.0,
            1.25,
            1.5,
            1.75,
            0.0,
            0.25,
            0.5,
            0.75,
            1.0,
        ],
    )
    * PI
)


ANGULAR_MEAN: list[tuple[ndarray, float, float, float]] = [
    # Angles, valid_mean, low, high
    (deg2rad([210, 190, 170, 150]), deg2rad(180), 0.0, TWOPI),
    (deg2rad([330, 350, 10, 30]), deg2rad(360), 0.0, TWOPI),
    (deg2rad([10, 20, 30]), deg2rad(20), 0.0, TWOPI),
    (deg2rad([355, 5, 15]), deg2rad(5), 0.0, TWOPI),
    (deg2rad([340, 15, 50]), deg2rad(15), 0.0, TWOPI),
    (deg2rad([210, 190, 170]), deg2rad(190), 0.0, TWOPI),
    (deg2rad([340, 350, 360]), deg2rad(350), 0.0, TWOPI),
    (deg2rad([-210, -190, -170, -150]), deg2rad(180), 0.0, TWOPI),
    (deg2rad([-330, -350, -10, -30]), deg2rad(0), 0.0, TWOPI),
    (deg2rad([-10, -20, -30]), deg2rad(340), 0.0, TWOPI),
    (deg2rad([-355, -5, -15]), deg2rad(355), 0.0, TWOPI),
    (deg2rad([-340, -15, -50]), deg2rad(345), 0.0, TWOPI),
    (deg2rad([-340, -350, -360]), deg2rad(10), 0.0, TWOPI),
    (deg2rad([-210, -190, -170]), deg2rad(170), 0.0, TWOPI),
    (deg2rad([-210, -190, 190]), deg2rad(170), 0.0, TWOPI),
    (deg2rad([-210, -190, 210, 190]), deg2rad(180), 0.0, TWOPI),
    (deg2rad([-330, -350, 330, 350]), deg2rad(0), 0.0, TWOPI),
    (deg2rad([-80, 20, 120]), deg2rad(20), 0.0, TWOPI),
    # Adjust low, high
    (deg2rad([210, 190, 170, 150]), deg2rad(180), -PI, PI),
    (deg2rad([330, 350, 10, 30]), deg2rad(0), -PI, PI),
    (deg2rad([10, 20, 30]), deg2rad(20), -PI, PI),
    (deg2rad([355, 5, 15]), deg2rad(5), -PI, PI),
    (deg2rad([340, 15, 50]), deg2rad(15), -PI, PI),
    (deg2rad([210, 190, 170]), deg2rad(-170), -PI, PI),
    (deg2rad([340, 350, 360]), deg2rad(-10), -PI, PI),
    (deg2rad([-210, -190, -170, -150]), deg2rad(180), 0.0, TWOPI),
    (deg2rad([-330, -350, -10, -30]), deg2rad(0), 0.0, TWOPI),
    (deg2rad([-10, -20, -30]), deg2rad(-20), -PI, PI),
    (deg2rad([-355, -5, -15]), deg2rad(-5), -PI, PI),
    (deg2rad([-340, -15, -50]), deg2rad(-15), -PI, PI),
    (deg2rad([-340, -350, -360]), deg2rad(10), -PI, PI),
    (deg2rad([-210, -190, -170]), deg2rad(170), -PI, PI),
    (deg2rad([-210, -190, 190]), deg2rad(170), -PI, PI),
    (deg2rad([-210, -190, 210, 190]), deg2rad(180), -PI, PI),
    (deg2rad([-330, -350, 330, 350]), deg2rad(0), -PI, PI),
    (deg2rad([-80, 20, 120]), deg2rad(20), -PI, PI),
]


WEIGHTED_ANGULAR_MEAN: list[tuple[ndarray, float, ndarray]] = [
    # Angles, valid_mean, weights
    (deg2rad([355, 5, 15]), deg2rad(3.99447), array([0.4, 0.3, 0.3])),
    (deg2rad([210, 190, 170]), deg2rad(200.1233420), array([0.6, 0.3, 0.1])),
    (deg2rad([-340, -15, -50]), deg2rad(339.4314), array([0.25, 0.35, 0.4])),
]


@pytest.mark.parametrize(
    ("unwrapped_angle", "wrapped_angle"),
    zip(UNWRAPPED_ANGLES, WRAPPED_NEG_PI),
)
def testWrapAngleNegPiPi(unwrapped_angle: float, wrapped_angle: float):
    """Test wrapAngleNegPiPi."""
    assert isclose(wrapAngleNegPiPi(unwrapped_angle), wrapped_angle)


@pytest.mark.parametrize(
    ("unwrapped_angle", "wrapped_angle"),
    zip(UNWRAPPED_ANGLES, WRAPPED_TWO_PI),
)
def testWrapAngle2Pi(unwrapped_angle: float, wrapped_angle: float):
    """Test wrapAngle2Pi."""
    assert isclose(wrapAngle2Pi(unwrapped_angle), wrapped_angle)


@pytest.mark.parametrize(("angles", "valid_mean", "low", "high"), ANGULAR_MEAN)
def testAngularMean(angles: ndarray, valid_mean: float, low: float, high: float):
    """Test different sets of angular means."""
    assert isclose(angularMean(angles, low=low, high=high), valid_mean)


@pytest.mark.parametrize(("angles", "valid_mean", "weights"), WEIGHTED_ANGULAR_MEAN)
def testAngularMeanWeights(angles: ndarray, valid_mean: float, weights: ndarray):
    """Test different sets of weighted angular means."""
    assert isclose(angularMean(angles, weights=weights), valid_mean)


def testAngularMeanBadWeights():
    """Test different sets of weighted angular means."""
    with pytest.raises(ShapeError):
        angularMean(deg2rad([20, 30, 40]), weights=array([2, 3]))


# [NOTE]: Values for testing residual calculation assuming angular and non-angular components.
#   Assumes degrees as inputs
RESIDUALS_VEC_1 = array(
    [360.0, 360.0, 359.0, 180.0, 1.0, 10.0, 180.0, 181.0, 240.0, 181.0, 2.0, 190.0, 361.0, 361.0],
)
RESIDUALS_VEC_2 = array(
    [0.0, 1.0, 2.0, 180.0, 1.0, 10.0, 50.0, 179.0, 30.0, 1.0, 190.0, 2.0, 1.0, 2.0],
)

ANGLES = ones_like(RESIDUALS_VEC_1, dtype=bool)
EXPECTED_ANGLES = array(
    [0.0, -1.0, -3.0, 0.0, 0.0, 0.0, 130.0, 2.0, -150.0, -180, 172.0, -172.0, 0.0, -1.0],
)

NOT_ANGLES = zeros_like(RESIDUALS_VEC_1, dtype=bool)
EXPECTED_NOT_ANGLES = RESIDUALS_VEC_1 - RESIDUALS_VEC_2

RESIDUAL_VALS_ANGLES = zip(RESIDUALS_VEC_1, RESIDUALS_VEC_2, ANGLES, EXPECTED_ANGLES)
RESIDUAL_VALS_NOT_ANGLES = zip(RESIDUALS_VEC_1, RESIDUALS_VEC_2, NOT_ANGLES, EXPECTED_NOT_ANGLES)


@pytest.mark.parametrize(("first", "second", "angular", "expected"), RESIDUAL_VALS_ANGLES)
def testResidualAngular(first: float, second: float, angular: bool, expected: float):
    """Test function for calculating the residual of angle values."""
    # Normal
    assert isclose(degrees(residual(radians(first), radians(second), angular)), expected)

    # Distributive
    assert isclose(
        degrees(residual(radians(-1.0 * first), radians(-1.0 * second), angular)),
        -expected,
    )

    # Not Commutative
    assert isclose(degrees(residual(radians(second), radians(first), angular)), -expected)

    # Invariant to wrapping
    if angular:
        assert isclose(
            degrees(residual(radians(first + 360.0), radians(second), angular)),
            expected,
        )


@pytest.mark.parametrize(("first", "second", "angular", "expected"), RESIDUAL_VALS_NOT_ANGLES)
def testResidualNotAngular(first: float, second: float, angular: bool, expected: float):
    """Test function for calculating residual of non-angle values."""
    # Normal
    assert isclose(degrees(residual(radians(first), radians(second), angular)), expected)

    # Distributive
    assert isclose(
        degrees(residual(radians(-1.0 * first), radians(-1.0 * second), angular)),
        -expected,
    )

    # Not Commutative
    assert isclose(degrees(residual(radians(second), radians(first), angular)), -expected)


def testResiduals():
    """Test vector function for calculating residuals of angle and non-angle components."""
    vec_1 = radians(RESIDUALS_VEC_1)
    vec_2 = radians(RESIDUALS_VEC_2)

    # Test angular values handled correctly.
    angles = residuals(vec_1, vec_2, angular=ANGLES)
    assert allclose(degrees(angles), EXPECTED_ANGLES)

    # Test non-angular values handled correctly.
    not_angles = residuals(vec_1, vec_2, angular=NOT_ANGLES)
    assert allclose(degrees(not_angles), EXPECTED_NOT_ANGLES)

    # Test mixed values handled correctly
    a = radians([10.1, 359.0, 200.0])
    b = radians([0.1, 1.0, 100.0])
    expected = [10.0, -2.0, 100.0]
    angular = array([False, True, False])
    mixed = residuals(a, b, angular)
    assert allclose(degrees(mixed), expected)

    # Test bad shape matches
    with pytest.raises(ShapeError):
        residuals(a, b, angular[:2])

    with pytest.raises(ShapeError):
        residuals(a[:2], b, angular)

    with pytest.raises(ShapeError):
        residuals(a, array([0.1, 1.0, 100.0, 2.0]), angular)
