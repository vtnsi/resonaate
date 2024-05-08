"""Defines statistical functions and tests."""

from __future__ import annotations

# Standard Library Imports
from typing import TYPE_CHECKING

# Third Party Imports
from numpy import logical_and, sqrt
from scipy.linalg import inv
from scipy.stats import chi2

if TYPE_CHECKING:
    # Third Party Imports
    from numpy import ndarray


def getStandardDeviation(confidence: float | ndarray, dim: float | ndarray) -> float | ndarray:
    r"""Determine the N-dimensional standard deviation.

    Examples:
        >>> getStandardDeviation(confidence=0.954499736103642, dim=1)
        2.0000000000000027
        >>> getStandardDeviation(confidence=0.954499736103642, dim=3)
        2.8328222253198794

    Args:
        confidence (``float | ndarray``): confidence region, N-dimensional confidence interval, equivalent to
            :math:`1 - \alpha`.
        dim (``float | ndarray``): degrees of freedom, or dimension, of the random variable.

    Returns:
        ``float | ndarray``: the N-dimensional standard deviation, :math:`sigma`.
    """
    return sqrt(chi2.ppf(confidence, dim))


def getConfidenceRegion(sigma: float | ndarray, dim: float | ndarray) -> float | ndarray:
    r"""Determine the N-dimensional confidence interval, or confidence region.

    Examples:
        >>> getConfidenceRegion(confidence=2, dim=1)
        0.954499736103642
        >>> getConfidenceRegion(confidence=2, dim=3)
        0.7385358700508888

    Args:
        sigma (``float | ndarray``): the N-dimensional standard deviation, :math:`sigma`.
        dim (``float | ndarray``): degrees of freedom, or dimension, of the random variable.

    Returns:
        ``float | ndarray``: confidence region, N-dimensional confidence interval, equivalent to
            :math:`1 - \alpha`.
    """
    return chi2.cdf(sigma**2, dim)


def chiSquareQuadraticForm(residual: ndarray, covariance: ndarray) -> float:
    r"""Calculate the chi-square quadratic form of an :math:`n-`dimensional` random vector, :math:`x`.

    The chi-square quadratic form is calculated as follows:

    .. math::

        q &= (x - \bar{x})^{T} P^{-1} (x - \bar{x}) \\
        &= \tilde{x}^{T} P^{-1} \tilde{x}

    where :math:`x\in\mathbb{R}^{n}` is the random vector with mean :math:`\bar{x}` and covariance :math:`P`. The
    value :math:`\tilde{x} = (x - \bar{x})` is known as the **residual** vector of :math:`x`. This equation results
    in the scalar random value, :math:`q`, which is said to have a chi-square distribution with :math:`n`
    degrees of freedom. This distribution is typically written as:

    .. math::

        q \sim \chi^{2}_{n}

    with mean and variance:

    .. math::

        E[q] &= n \\
        E[(q - n)^{2}] &= 2n \\

    References:
        #. cite:t:`bar-shalom_2001_estimation`, Section 1.4.7, Eqn 1.4.17-1, Pg 57
        #. cite:t:`crassidis_2012_optest`, Section 4.3 & C.6

    Args:
        residual (``ndarray``): the residual vector of the random vector being tested,
            :math:`\tilde{x} = (x - \bar{x})`.
        covariance (``ndarray``): the covariance associated with the random vector being tested, :math:`P`.

    Returns:
        ``float``: :math:`q`, the chi-square quadratic form of the random vector :math:`x`.
    """
    return residual.T.dot(inv(covariance).dot(residual))


def oneSidedChiSquareTest(
    metric: float | ndarray,
    alpha: float | ndarray,
    dof: float | ndarray,
    runs: int = 1,
) -> bool | ndarray:
    r"""Test if the given metric lies within the one-sided (upper) confidence interval of a chi-square distribution.

    The confidence is defined as :math:`1 - \alpha`, so a 95% confidence interval requires :math:`\alpha=0.05`.
    A 95% confidence interval of a one-sided chi-square distribution with 2 degrees of freedom results in

    .. math::

        \chi^{2}_{2} (0.95) \simeq 5.99

    Examples:
        >>> oneSidedChiSquareTest(6, 0.05, 2)
        False
        >>> oneSidedChiSquareTest(5.9, 0.05, 2)
        True

    Args:
        metric (``float | ndarray``): value to test against the null hypothesis.
        alpha (``float | ndarray``): significance level, or the test p-value.
        dof (``float | ndarray``): degrees of freedom of the chi-square distributed variable.
        runs (``int``): number of independent runs that the metric was averaged over. This allows testing metrics that
            are time averaged or found via Monte Carlo analysis. Defaults to 1.

    Returns:
        ``bool | ndarray``: whether the null hypothesis is rejected (``False``) or not rejected (``True``).
    """
    upper_bound = chi2.isf(alpha, dof * runs) / runs
    return metric < upper_bound


def twoSidedChiSquareTest(
    metric: float | ndarray,
    alpha: float | ndarray,
    dof: float | ndarray,
    runs: int = 1,
) -> bool | ndarray:
    r"""Test if the given metric lies within the two-sided confidence interval of a chi-square distribution.

    The confidence is defined as :math:`1 - \alpha`, so a 95% confidence interval requires :math:`\alpha=0.05`.
    A 95% confidence interval of a two-sided chi-square distribution with 50 degrees of freedom results in

    .. math::

        [\chi^{2}_{50} (0.025), \chi^{2}_{50} (0.975)] \simeq [32.3, 71.4]

    Examples:
        >>> twoSidedChiSquareTest(30, 0.05, 50)
        False
        >>> twoSidedChiSquareTest(55, 0.05, 50)
        True
        >>> twoSidedChiSquareTest(72, 0.05, 50)
        False

    Args:
        metric (``float | ndarray``): value to test against the null hypothesis.
        alpha (``float | ndarray``): significance level, or the test p-value.
        dof (``float | ndarray``): degrees of freedom of the chi-square distributed variable.
        runs (``int``): number of independent runs that the metric was averaged over. This allows testing metrics that
            are time averaged or found via Monte Carlo analysis. Defaults to 1.

    Returns:
        ``bool | ndarray``: whether the null hypothesis is rejected (``False``) or not rejected (``True``).
    """
    lower_bound = chi2.isf(1.0 - alpha * 0.5, dof * runs) / runs
    upper_bound = chi2.isf(alpha * 0.5, dof * runs) / runs
    return logical_and(lower_bound < metric, metric < upper_bound)
