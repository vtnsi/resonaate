# Standard Library Imports
# Third Party Imports
import pytest
from numpy.random import random_sample

try:
    # RESONAATE Imports
    from resonaate.physics.statistics import (
        chiSquareQuadraticForm,
        oneSidedChiSquareTest,
        twoSidedChiSquareTest,
    )
except ImportError as error:
    raise Exception(f"Please ensure you have appropriate packages installed:\n {error}") from error
# Testing Imports


ONE_SIDED_TESTS = [
    (6, 0.05, 2, 1, False),
    (5.9, 0.05, 2, 1, True),
    (2.4, 0.05, 2, 100, False),
    (2.3, 0.05, 2, 100, True),
]


TWO_SIDED_TESTS = [
    (30, 0.05, 50, 1, False),
    (55, 0.05, 50, 1, True),
    (72, 0.05, 50, 1, False),
    (1.62, 0.05, 2, 100, False),
    (2.1, 0.05, 2, 100, True),
    (2.42, 0.05, 2, 100, False),
    (0.87, 0.05, 1, 500, False),
    (1.1, 0.05, 1, 500, True),
    (1.128, 0.05, 1, 500, False),
    (0.64, 0.05, 1, 50, False),
    (1.01, 0.05, 1, 50, True),
    (1.44, 0.05, 1, 50, False),
]


def testChiSquareQuadraticForm():
    """Test chi-square quadratic form function."""
    for scale in range(1, 5):
        matrix = scale * random_sample((3, 3)) + scale
        vector = random_sample(
            3,
        )
        cov = matrix.dot(matrix.T)

        quad_form = chiSquareQuadraticForm(vector, cov)
        assert quad_form > 0


@pytest.mark.parametrize(("metric", "alpha", "dof", "runs", "passes"), ONE_SIDED_TESTS)
def testOneSidedChiSquare(metric, alpha, dof, runs, passes):
    """Test one-sided chi-square hypothesis test."""
    assert passes == oneSidedChiSquareTest(metric, alpha, dof, runs=runs)


@pytest.mark.parametrize(("metric", "alpha", "dof", "runs", "passes"), TWO_SIDED_TESTS)
def testTwoSidedChiSquare(metric, alpha, dof, runs, passes):
    """Test two-sided chi-square hypothesis test."""
    assert passes == twoSidedChiSquareTest(metric, alpha, dof, runs=runs)
