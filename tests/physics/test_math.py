# Standard Library Imports
# Third Party Imports
import pytest
from numpy import array, deg2rad, isclose, linspace

try:
    # RESONAATE Imports
    from resonaate.physics.constants import PI, TWOPI
    from resonaate.physics.math import ShapeError, angularMean, wrapAngle2Pi, wrapAngleNegPiPi
except ImportError as error:
    raise Exception(f"Please ensure you have appropriate packages installed:\n {error}") from error
# Testing Imports


UNWRAPPED_ANGLES = linspace(-5, 5, 41) * PI


WRAPPED_NEG_PI = (
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
        ]
    )
    * PI
)


WRAPPED_TWO_PI = (
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
        ]
    )
    * PI
)


ANGULAR_MEAN = [
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


WEIGHTED_ANGULAR_MEAN = [
    # Angles, valid_mean, low, high
    (deg2rad([355, 5, 15]), deg2rad(3.99447), array([0.4, 0.3, 0.3])),
    (deg2rad([210, 190, 170]), deg2rad(200.1233420), array([0.6, 0.3, 0.1])),
    (deg2rad([-340, -15, -50]), deg2rad(339.4314), array([0.25, 0.35, 0.4])),
]


@pytest.mark.parametrize(
    ("unwrapped_angle", "wrapped_angle"), zip(UNWRAPPED_ANGLES, WRAPPED_NEG_PI)
)
def testwrapAngleNegPiPi(unwrapped_angle, wrapped_angle):
    """Test wrapAngleNegPiPi."""
    assert isclose(wrapAngleNegPiPi(unwrapped_angle), wrapped_angle)


@pytest.mark.parametrize(
    ("unwrapped_angle", "wrapped_angle"), zip(UNWRAPPED_ANGLES, WRAPPED_TWO_PI)
)
def testwrapAngle2Pi(unwrapped_angle, wrapped_angle):
    """Test wrapAngle2Pi."""
    assert isclose(wrapAngle2Pi(unwrapped_angle), wrapped_angle)


@pytest.mark.parametrize(("angles", "valid_mean", "low", "high"), ANGULAR_MEAN)
def testAngularMean(angles, valid_mean, low, high):
    """Test different sets of angular means."""
    assert isclose(angularMean(angles, low=low, high=high), valid_mean)


@pytest.mark.parametrize(("angles", "valid_mean", "weights"), WEIGHTED_ANGULAR_MEAN)
def testAngularMeanWeights(angles, valid_mean, weights):
    """Test different sets of weighted angular means."""
    assert isclose(angularMean(angles, weights=weights), valid_mean)


def testAngularMeanBadWeights():
    """Test different sets of weighted angular means."""
    with pytest.raises(ShapeError):
        angularMean(deg2rad([20, 30, 40]), weights=array([2, 3]))
