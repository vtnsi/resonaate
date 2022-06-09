"""General mathematics functions that provided extended capability to `numpy`_ and `scipy`_.

.. _scipy: https://docs.scipy.org/doc/scipy/index.html
.. _numpy: https://numpy.org/doc/stable/
"""
# Standard Library Imports
from typing import Optional
# Third Party Imports
from numpy import (
    amin, arccos, arctan2, array, clip, cos, diag, eye, fabs, finfo, fmod,
    ndarray, real, remainder, sign, sin, spacing
)
# Third Party Imports
from numpy.linalg import multi_dot, cholesky, LinAlgError
from scipy.linalg import norm, eigvals, svd
# RESONAATE Imports
from . import constants as const
from ..common.logger import resonaateLogError
from ..common.exceptions import ShapeError


_MAX_ITER = 100
"""``int``: maximum number of iterations for iterative algorithms."""
_RTOL = 4 * finfo(float).eps
"""``float``: allowable relative error tolerance for iterative algorithms."""
_ATOL = 1.48e-8
"""``float``: allowable absolute error tolerance for iterative algorithms."""


def rot1(angle: float) -> ndarray:
    r"""Calculate the first-axis rotation matrix, in radians.

    Args:
        angle (``float``): angle rotated through, (radians).

    Returns:
        ``ndarray``: 3x3 rotation matrix.
    """
    return array([
        [1, 0, 0],
        [0, cos(angle), sin(angle)],
        [0, -sin(angle), cos(angle)]
    ])


def rot2(angle: float) -> ndarray:
    r"""Calculate the second-axis rotation matrix, in radians.

    Args:
        angle (``float``): angle rotated through, (radians).

    Returns:
        ``ndarray``: 3x3 rotation matrix.
    """
    return array([
        [cos(angle), 0, -sin(angle)],
        [0, 1, 0],
        [sin(angle), 0, cos(angle)]
    ])


def rot3(angle: float) -> ndarray:
    r"""Calculate the third-axis rotation matrix, in radians.

    Args:
        angle (``float``): angle rotated through, (radians).

    Returns:
        ``ndarray``: 3x3 rotation matrix.
    """
    return array([
        [cos(angle), sin(angle), 0],
        [-sin(angle), cos(angle), 0],
        [0, 0, 1]
    ])


def dotRot1(angle: float, omega: ndarray) -> ndarray:
    r"""Calculate the time derivative of the first-axis rotation matrix, in radians.

    The rotation matrix time derivative is defined as

    .. math::

        \dot{R}^{A}_{B} = [w_{A}]_{\times}R^{A}_{B} = R^{A}_{B}[w_{B}]_{\times}

    where :math:`R^{A}_{B}` is the rotation from frame :math:`B` to frame :math:`A`, :math:`w_{A}`
    is the angular velocity vector of frame :math:`A` relative to frame :math:`B`, :math:`w_{B}`
    is the angular velocity vector of frame :math:`B` relative to frame :math:`A`, and
    :math:`[]_{\times}` is the skew-symmetric operator (see :func:`~.skewSymmetric`). Therefore,
    the derivative of the first-axis rotation matrix is

    .. math::

        \dot{R}_{1} = R_{1}[w_{1}]_{\times}

    Args:
        angle (``float``): angle rotated through, (radians).
        omega (``ndarray``): 3x1 angular velocity vector of the source frame relative to the
            destination frame, (radians/sec).

    Returns:
        ``ndarray``: 3x3 matrix time derivative of rotation matrix.
    """
    return rot1(angle).dot(skewSymmetric(omega))


def dotRot2(angle: float, omega: ndarray) -> ndarray:
    r"""Calculate the time derivative of the second-axis rotation matrix, in radians.

    The rotation matrix time derivative is defined as

    .. math::

        \dot{R}^{A}_{B} = [w_{A}]_{\times}R^{A}_{B} = R^{A}_{B}[w_{B}]_{\times}

    where :math:`R^{A}_{B}` is the rotation from frame :math:`B` to frame :math:`A`, :math:`w_{A}`
    is the angular velocity vector of frame :math:`A` relative to frame :math:`B`, :math:`w_{B}`
    is the angular velocity vector of frame :math:`B` relative to frame :math:`A`, and
    :math:`[]_{\times}` is the skew-symmetric operator (see :func:`~.skewSymmetric`). Therefore,
    the derivative of the second-axis rotation matrix is

    .. math::

        \dot{R}_{2} = R_{2}[w_{2}]_{\times}

    Args:
        angle (``float``): angle rotated through, (radians).
        omega (``ndarray``): 3x1 angular velocity vector of the source frame relative to the
            destination frame, (radians/sec).

    Returns:
        ``ndarray``: 3x3 matrix time derivative of rotation matrix.
    """
    return rot2(angle).dot(skewSymmetric(omega))


def dotRot3(angle: float, omega: ndarray) -> ndarray:
    r"""Calculate the time derivative of the third-axis rotation matrix, in radians.

    The rotation matrix time derivative is defined as

    .. math::

        \dot{R}^{A}_{B} = [w_{A}]_{\times}R^{A}_{B} = R^{A}_{B}[w_{B}]_{\times}

    where :math:`R^{A}_{B}` is the rotation from frame :math:`B` to frame :math:`A`, :math:`w_{A}`
    is the angular velocity vector of frame :math:`A` relative to frame :math:`B`, :math:`w_{B}`
    is the angular velocity vector of frame :math:`B` relative to frame :math:`A`, and
    :math:`[]_{\times}` is the skew-symmetric operator (see :func:`~.skewSymmetric`). Therefore,
    the derivative of the third-axis rotation matrix is

    .. math::

        \dot{R}_{2} = R_{2}[w_{2}]_{\times}

    Args:
        angle (``float``): angle rotated through, (radians).
        omega (``ndarray``): 3x1 angular velocity vector of the source frame relative to the
            destination frame, (radians/sec).

    Returns:
        ``ndarray``: 3x3 matrix time derivative of rotation matrix.
    """
    return rot3(angle).dot(skewSymmetric(omega))


def skewSymmetric(w: ndarray) -> ndarray:
    r"""Return the skew-symmetric matrix of a vector.

    For any vector :math:`w=[w_1 , w_2 , w_3]^\mathrm{T}\in \mathbb{R}^3`, define the
    skew-symmetric operator, :math:`[\cdot]_{\times}` as

    .. math::

        [w]_{\times} \triangleq\left[\begin{array}{ccc}
            0 & -w_{3} & w_{2} \\
            w_{3} & 0 & -w_{1} \\
            -w_{2} & w_{1} & 0 \\
        \end{array}\right] \in \mathbb{R}^{3 \times 3}

    Args:
        w (``ndarray``): 3x1 vector from which to calculate the skew-symmetric matrix.

    Returns:
        ``ndarray``: corresponding 3x3 skew-symmetric matrix.
    """
    # pylint: disable=invalid-name
    return array(
        [
            [0, -w[2], w[1]],
            [w[2], 0, -w[0]],
            [-w[1], w[1], 0],
        ]
    )


# [REVIEW]: Port of nearestSPD.m found online.
def nearestPD(original_mat: ndarray) -> ndarray:
    r"""Find the nearest positive-definite matrix to input.

    References:
        #. :cite:t:`derrico_nearestspd`
        #. :cite:t:`higham_laa_1988_pd`

    Args:
        original_mat (``ndarray``): original matrix that is not positive definite.

    Returns:
        ``ndarray``: updated matrix, corrected to be positive definite.
    """
    # symmetrize matrix, perform singular value decomposition, compute symmetric polar factor
    sym_mat = (original_mat + original_mat.T) / 2
    _, singular, right_mat = svd(sym_mat)
    pol_factor = multi_dot((right_mat.T, diag(singular), right_mat))

    # Find A-hat in formula from paper, symmetrize it
    pd_mat = (sym_mat + pol_factor) / 2
    sym_pd_mat = (pd_mat + pd_mat.T) / 2

    # Return if positive-definite
    if isPD(sym_pd_mat):
        return sym_pd_mat

    _spacing = spacing(norm(original_mat))
    # The above is different from [1]. It appears that MATLAB's `chol` Cholesky
    # decomposition will accept matrixes with exactly 0-eigenvalue, whereas
    # numpy cholesky will not. So where [1] uses `eps(min_eig)` (where `eps` is Matlab
    # for `np.spacing`), we use the above definition. CAVEAT: our `spacing`
    # will be much larger than [1]'s `eps(min_eig)`, since `min_eig` is usually on
    # the order of 1e-16, and `eps(1e-16)` is on the order of 1e-34, whereas
    # `spacing` will, for Gaussian random matrixes of small dimension, be on
    # the order of 1e-16. In practice, both ways converge, as the unit test
    # below suggests.
    identity = eye(original_mat.shape[0])
    k = 1
    while not isPD(sym_pd_mat):
        min_eig = amin(real(eigvals(sym_pd_mat)))
        sym_pd_mat += identity * (-min_eig * k**2 + _spacing)
        k += 1

    return sym_pd_mat


def wrapAngleNegPiPi(angle: float) -> float:
    r"""Force angle into range of :math:`(-\pi, \pi]`."""
    # Remainder takes sign of divisor (second arg)
    angle = remainder(angle, const.TWOPI)
    if fabs(angle) > const.PI:
        angle -= const.TWOPI * sign(angle)
    return angle


def wrapAngle2Pi(angle: float) -> float:
    r"""Force angle into range of :math:`[0, 2\pi)`."""
    # Fmod takes sign of dividend (first arg)
    angle = fmod(angle, const.TWOPI)
    if angle < 0:
        angle += const.TWOPI
    return angle


def fpe_equals(value: float, expected: float) -> float:  # pylint: disable=invalid-name
    r"""Utility for checking that `value` and `expected` are equal within the bounds of floating point error (FPE).

    Args:
        value (``float``): Value being compared.
        expected (``float``): Value that `value` is expected to be without FPE

    Returns:
        ``bool``: If `True`, then it should be safe to assume that `value == expected` and the `value` is just
        misrepresented due to FPE.
    """
    return fabs(value - expected) < finfo(float).resolution  # pylint: disable=no-member


def safeArccos(arg: float) -> float:
    r"""Safely perform an :math:`\arccos{}` calculation.

    It's possible due to floating point error/truncation that a value that should be
    1.0 or -1.0 could end up being e.g. 1.0000000002 or -1.000000002. These values result
    in ``numpy.arccos()`` throwing a domain warning and breaking functionality. ``safeArccos()``
    checks to see if the given ``arg`` is within the proper domain, and if not, will correct
    the value before performing the :math:`\arccos{}` calculation.

    Raises:
        ``ValueError``: if the given ``arg`` is *actually* outside the domain of :math:`\arccos{}`

    Args:
        arg (``ndarray``): value(s) to perform :math:`\arccos{}` calculation on

    Returns:
        (``ndarray``): result of :math:`\arccos{}` calculation on given ``arg``, radians
    """
    # Check for valid arccos domain
    if fabs(arg) <= 1.0:
        return arccos(arg)
    # else
    if not fpe_equals(fabs(arg), 1.0):
        msg = f"`safeArccos()` used on non-truncation/rounding error. Value: {arg}"
        resonaateLogError(msg)
        raise ValueError(arg)
    return arccos(clip(arg, -1, 1))


def isPD(matrix: ndarray) -> bool:
    """Determine whether a matrix is positive-definite, via ``numpy.linalg.cholesky``.

    Args:
        matrix (``ndarray``): input matrix to be checked for positive definiteness.

    Returns:
        ``bool``: whether the given matrix is numerically positive definiteness.
    """
    try:
        cholesky(matrix)
        return True

    except LinAlgError:
        return False


def angularMean(
    angles: ndarray, weights: Optional[ndarray] = None,
    high: Optional[float] = const.TWOPI, low: Optional[float] = 0.0
) -> float:
    r"""Calculate the (possibly weighted) mean of `angles` within a given range.

    The weighted angular mean is defined as

    .. math::

        \bar{\alpha}=\operatorname{atan2}\left(
            \sum_{j=1}^{n} \sin(\alpha_{j})w_{j}, \sum_{j=1}^{n} \cos(\alpha_{j})w_{j}
        \right)

    where :math:`\alpha_{j}` is a single angular value and :math:`w_{j}` is its corresponding
    weight. If no array of `weights` is provided, then
    :math:`w_{j} = 1 \quad\forall\quad j=1\ldots n`. This is by definition the circular mean.

    See Also:
        https://en.wikipedia.org/wiki/Circular_mean

    Args:
        angles (``ndarray``): Nx1 input array of angles, (radians).
        weights (``ndarray``, optional): Nx1 array of weights to compute a weighted mean. Defaults to
            ``None`` which means the angular values are equally weighted and the _circular_ mean
            is computed.
        high (``float``, optional): high boundary for mean range. Defaults to :math:`2\Pi`.
        low (``float``, optional): low boundary for mean range. Defaults to 0.0.

    Raises:
        :class:`.ShapeError`: raised if computing a weighted mean and the input array and the
            weight array do not have the same length.

    Returns:
        ``float``: the angular mean of the given angles.
    """
    sin_angles = sin((angles - low) * const.TWOPI / (high - low))
    cos_angles = cos((angles - low) * const.TWOPI / (high - low))

    if weights is not None:
        if angles.shape != weights.shape:
            msg = f"`angularMean()` wasn't passed arrays with equal length, {angles.shape} != {weights.shape}"
            resonaateLogError(msg)
            raise ShapeError(msg)

        # Normalize weights
        weights = weights / norm(weights)
        # Inner product
        sin_mean = sin_angles.dot(weights)
        cos_mean = cos_angles.dot(weights)

    else:
        # Because of arctangent the mean == sum (equal weighting is redundant)
        sin_mean = sin_angles.sum()
        cos_mean = cos_angles.sum()

    # Determine the arctangent of the sine & cosine means, then rescale to [0, 2π]
    result_mean = wrapAngle2Pi(arctan2(sin_mean, cos_mean))
    return result_mean * (high - low) / const.TWOPI + low
