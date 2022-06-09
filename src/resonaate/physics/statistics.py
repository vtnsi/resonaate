"""Defines statistical functions and tests."""
# Third Party Imports
from numpy import ndarray
from numpy.linalg import inv
from scipy.stats import chi2


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


def oneSidedChiSquareTest(metric: float, alpha: float, dof: float, runs: int = 1) -> bool:
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
        metric (``float``): value to test against the null hypothesis.
        alpha (``float``): significance level, or the test p-value.
        dof (``float``): degrees of freedom of the chi-square distributed variable.
        runs (``int``): number of independent runs that the metric was averaged over. This allows testing metrics that
            are time averaged or found via Monte Carlo analysis. Defaults to 1.

    Returns:
        ``bool``: whether the null hypothesis is rejected (``False``) or not rejected (``True``).
    """
    upper_bound = chi2.isf(alpha, dof * runs) / runs
    return metric < upper_bound


def twoSidedChiSquareTest(metric: float, alpha: float, dof: float, runs: int = 1) -> bool:
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
        metric (``float``): value to test against the null hypothesis.
        alpha (``float``): significance level, or the test p-value.
        dof (``float``): degrees of freedom of the chi-square distributed variable.
        runs (``int``): number of independent runs that the metric was averaged over. This allows testing metrics that
            are time averaged or found via Monte Carlo analysis. Defaults to 1.

    Returns:
        ``bool``: whether the null hypothesis is rejected (``False``) or not rejected (``True``).
    """
    lower_bound = chi2.isf(1.0 - alpha * 0.5, dof * runs) / runs
    upper_bound = chi2.isf(alpha * 0.5, dof * runs) / runs
    return lower_bound < metric < upper_bound
