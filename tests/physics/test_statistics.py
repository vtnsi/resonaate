from __future__ import annotations

# Third Party Imports
import pytest
from numpy import allclose, array, isclose
from numpy.random import random_sample

# RESONAATE Imports
from resonaate.physics.statistics import (
    chiSquareQuadraticForm,
    getConfidenceRegion,
    getStandardDeviation,
    oneSidedChiSquareTest,
    twoSidedChiSquareTest,
)

ONE_SIDED_TESTS: list[tuple[float, float, int, int, bool]] = [
    (6, 0.05, 2, 1, False),
    (5.9, 0.05, 2, 1, True),
    (2.4, 0.05, 2, 100, False),
    (2.3, 0.05, 2, 100, True),
]


TWO_SIDED_TESTS: list[tuple[float, float, int, int, bool]] = [
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


CONFIDENCE_SIGMA_DOF: list[tuple[float, int, int]] = [
    (0.682689492137086, 1, 1),
    (0.954499736103642, 2, 1),
    (0.997300203936740, 3, 1),
    (0.3934693402873665, 1, 2),
    (0.8646647167633873, 2, 2),
    (0.9888910034617577, 3, 2),
    (0.19874804309879915, 1, 3),
    (0.7385358700508888, 2, 3),
    (0.9707091134651118, 3, 3),
    (0.09020401043104986, 1, 4),
    (0.5939941502901616, 2, 4),
    (0.9389005190396673, 3, 4),
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
def testOneSidedChiSquare(metric: float, alpha: float, dof: int, runs: int, passes: bool):
    """Test one-sided chi-square hypothesis test."""
    assert passes == oneSidedChiSquareTest(metric, alpha, dof, runs=runs)


@pytest.mark.parametrize(("start_idx", "stop_idx"), [(0, 2), (2, 4)])
def testOneSidedChiSquareArray(start_idx: int, stop_idx: int):
    """Test one-sided chi-square hypothesis test with array inputs."""
    data = array(ONE_SIDED_TESTS)
    res = oneSidedChiSquareTest(
        metric=data[start_idx:stop_idx, 0],
        alpha=data[start_idx:stop_idx, 1],
        dof=data[start_idx:stop_idx, 2],
        runs=data[start_idx, 3],
    )
    assert all(data[start_idx:stop_idx, 4] == res)


@pytest.mark.parametrize(("metric", "alpha", "dof", "runs", "passes"), TWO_SIDED_TESTS)
def testTwoSidedChiSquare(metric: float, alpha: float, dof: int, runs: int, passes: bool):
    """Test two-sided chi-square hypothesis test."""
    assert passes == twoSidedChiSquareTest(metric, alpha, dof, runs=runs)


@pytest.mark.parametrize(("start_idx", "stop_idx"), [(0, 3), (3, 6), (6, 9), (9, 12)])
def testTwoSidedChiSquareArray(start_idx: int, stop_idx: int):
    """Test two-sided chi-square hypothesis test with array inputs."""
    data = array(TWO_SIDED_TESTS)
    res = twoSidedChiSquareTest(
        metric=data[start_idx:stop_idx, 0],
        alpha=data[start_idx:stop_idx, 1],
        dof=data[start_idx:stop_idx, 2],
        runs=data[start_idx, 3],
    )
    assert all(data[start_idx:stop_idx, 4] == res)


@pytest.mark.parametrize(("confidence", "sigma", "dof"), CONFIDENCE_SIGMA_DOF)
def testStandardDeviation(confidence: float, sigma: int, dof: int):
    """Test the N-dimensional standard deviation function with array inputs."""
    assert isclose(sigma, getStandardDeviation(confidence, dof))


def testStandardDeviationArray():
    """Test the N-dimensional standard deviation function with array inputs."""
    confidence = array(CONFIDENCE_SIGMA_DOF)[:, 0]
    sigma = array(CONFIDENCE_SIGMA_DOF)[:, 1]
    dof = array(CONFIDENCE_SIGMA_DOF)[:, 2]
    assert allclose(sigma, getStandardDeviation(confidence, dof))


@pytest.mark.parametrize(("confidence", "sigma", "dof"), CONFIDENCE_SIGMA_DOF)
def testConfidenceRegion(confidence: float, sigma: int, dof: int):
    """Test the N-dimensional confidence region function."""
    assert isclose(confidence, getConfidenceRegion(sigma, dof))


def testConfidenceRegionArray():
    """Test the N-dimensional confidence region function with array inputs."""
    confidence = array(CONFIDENCE_SIGMA_DOF)[:, 0]
    sigma = array(CONFIDENCE_SIGMA_DOF)[:, 1]
    dof = array(CONFIDENCE_SIGMA_DOF)[:, 2]
    assert allclose(confidence, getConfidenceRegion(sigma, dof))
