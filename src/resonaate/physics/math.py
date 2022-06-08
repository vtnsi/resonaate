# Standard Library Imports
# Third Party Imports
from numpy import spacing, sin, cos, asarray, real, diag, eye
from numpy import min as np_min
from numpy import cross as np_cross
from numpy import abs as np_abs, arccos, fix
from numpy.linalg import multi_dot, cholesky, LinAlgError
from scipy.linalg import norm, eigvals, svd
# RESONAATE Imports
from . import constants as const


# [TODO] Probably should put dotROT1() and dotROT2() here as well


def dotRot3(angle, omega):
    """Return the derivative of third-axis rotation matrix. Assumes radians."""
    return asarray([
        [-omega * sin(angle), omega * cos(angle), 0],
        [-omega * cos(angle), -omega * sin(angle), 0],
        [0, 0, 0]
    ])


def rot1(angle):
    """Return the first-axis rotation matrix. Assumes radians."""
    return asarray([
        [1, 0, 0],
        [0, cos(angle), sin(angle)],
        [0, -sin(angle), cos(angle)]
    ])


def rot2(angle):
    """Return the second-axis rotation matrix. Assumes radians."""
    return asarray([
        [cos(angle), 0, -sin(angle)],
        [0, 1, 0],
        [sin(angle), 0, cos(angle)]
    ])


def rot3(angle):
    """Return the third-axis rotation matrix. Assumes radians."""
    return asarray([
        [cos(angle), sin(angle), 0],
        [-sin(angle), cos(angle), 0],
        [0, 0, 1]
    ])


def cross(vec1, vec2, **kwargs):
    """Re-implement numpy cross function to accept 1D & 2D vectors."""
    if vec1.shape == (3, 1):
        vec1 = vec1.reshape(3)
    elif vec1.shape == (2, 1):
        vec1 = vec1.reshape(2)
    elif vec1.shape[0] not in (3, 2):
        raise ValueError("incompatible dimensions for cross product \n(dimension must be 2 or 3)")

    if vec2.shape == (3, 1):
        vec2 = vec2.reshape(3)
    elif vec2.shape == (2, 1):
        vec2 = vec2.reshape(2)
    elif vec2.shape[0] not in (3, 2):
        raise ValueError("incompatible dimensions for cross product \n(dimension must be 2 or 3)")

    return np_cross(vec1, vec2, **kwargs)


# [REVIEW] Port of nearestSPD.m found online.
def nearestPD(original_mat):
    """Find the nearest positive-definite matrix to input.

    A Python/Numpy port of John D'Errico's `nearestSPD` MATLAB code [1], which
    credits [2].

    [1] https://www.mathworks.com/matlabcentral/fileexchange/42885-nearestspd

    [2] N.J. Higham, "Computing a nearest symmetric positive semidefinite
    matrix" (1988): https://doi.org/10.1016/0024-3795(88)90223-6
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
        min_eig = np_min(real(eigvals(sym_pd_mat)))
        sym_pd_mat += identity * (-min_eig * k**2 + _spacing)
        k += 1

    return sym_pd_mat


def normalizeAngle(angle):
    """Force angle into range of [0, 2pi], then into [-const.PI, const.PI]."""
    angle = angle % (2 * const.PI)
    if angle > const.PI:
        angle -= 2 * const.PI
    return angle


def safeArccos(arg):
    """Safely perform an arccos calculation.

    It's possible due to floating point error/truncation that a value that should be
    1.0 or -1.0 could end up being e.g. 1.0000000002 or -1.000000002. These values result
    in `numpy.arccos()` throwing a domain warning and breaking functionality. `safeArccos`
    checks to see if the given `arg` is within the proper domain, and if not, will correct
    the value before performing the `arccos` calculation.

    Warning:
        There are certain cases where this function could give a valid result
        where there shouldn't be one. For example, if the given `arg` is _really_
        outside the domain of `arccos` (i.e. not just due to floating point error/truncation)
        this function will still return a valid result. Use with care.

    Args:
        arg (``np.ndarray``): value(s) to perform `arccos` calculation on

    Returns:
        (``np.ndarray``): result of `arccos` calculation on given `arg`
    """
    if np_abs(arg) > 1.0:
        assert np_abs(arg) - 1.0 < 1e-15, "`safeArgcos()` used on non-truncation/rounding error"
        return arccos(fix(arg))
    else:
        return arccos(arg)


def isPD(matrix):
    """Return true when input is positive-definite, via Cholesky."""
    try:
        cholesky(matrix)
        return True

    except LinAlgError:
        return False
