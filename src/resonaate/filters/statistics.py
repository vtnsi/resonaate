"""Defines statistical functions and tests for analyzing filtering algorithms."""
# Standard Library Imports
from abc import ABCMeta
# Third Party Imports
from numpy import matmul
from numpy.linalg import inv
# RESONAATE Imports
from ..scenario.config.base import NO_SETTING


class Nis(metaclass=ABCMeta):
    """Normalized Innovations Squared (NIS) class.

    References:
        :cite:t:`bar-shalom_2001_estimation`, Section 11.2.2, Eqn 11.2.2-1
    """

    def __init__(self, maneuver_gate_val):
        """Initialize Nis Class.

        Args:
            current_nis (``float``): NIS at the current timestep
        """
        self.current_nis = None
        self.maneuver_gate_val = maneuver_gate_val

    def calculateNIS(self, residual, innov_cvr):
        """Calculate Standard Nis.

        Args:
            residual (`np.ndarray`): nzx1 measurement residual vector
            innov_cvr (`np.ndarray`): innovation covariance matrix
        """
        self.current_nis = matmul(matmul(residual.T, inv(innov_cvr)), residual)


class SlidingNis(Nis):
    """Calculate the sliding window normalized innovations squared of a filter update.

    References:
        :cite:t:`bar-shalom_2001_estimation`, Section 11.2.2, Eqn 11.2.2-3

    It has s*nz degrees of freedom, where 's' is the size of the sliding window.

    Note:
        [TODO]: Unverified calculation, rethink function arguments
    """

    def __init__(self, maneuver_gate_val, step=4):
        """Initialize Sliding Nis.

        Args:
            step (``int``): number of timesteps of NIS values to hold onto
            nis_list (``list``): list of previous NIS values of an estimate's filter object
        """
        super().__init__(maneuver_gate_val)

        self.step = step
        self.nis_list = []

    def calculateNIS(self, residual, innov_cvr):
        """Calculate Sliding Nis.

        Args:
            residual (`np.ndarray`): nzx1 measurement residual vector
            innov_cvr (`np.ndarray`): innovation covariance matrix
        """
        if len(self.nis_list) >= self.step:  # should NEVER be greater than s, but '>' just in case
            self.nis_list.pop(0)
        self.nis_list.append(matmul(matmul(residual.T, inv(innov_cvr)), residual))

        self.current_nis = sum(self.nis_list)


class FadingMemoryNis(Nis):
    """Calculate the fading memory average normalized innovations squared of a filter update.

    References:
        :cite:t:`bar-shalom_2001_estimation`, Section 11.2.2, Eqn 11.2.2-5

    It has nz*(1+alpha)/(1-alpha) degrees of freedom.

    Note:
        [TODO]: Unverified calculation
    """

    def __init__(self, maneuver_gate_val, alpha=0.8):
        """Initialize Fading Memory Nis.

        Args:
            alpha (float): fading scale such that 0 < alpha < 1
            prior_nis (float): maneuver_metric value from the prior timestep
        """
        super().__init__(maneuver_gate_val)
        self.alpha = alpha
        self.prior_nis = 0.0

    def calculateNIS(self, residual, innov_cvr):
        """Calculate Fading Memory Nis.

        Args:
            residual (`np.ndarray`): nzx1 measurement residual vector
            innov_cvr (`np.ndarray`): innovation covariance matrix
        """
        current_nis = matmul(matmul(residual.T, inv(innov_cvr)), residual)
        self.current_nis = self.alpha * self.prior_nis + current_nis
        self.prior_nis = self.current_nis


STANDARD_NIS_LABEL = 'standard_nis'
"""str: Constant string used to describe standard NIS method."""

SLIDING_NIS_LABEL = 'sliding_nis'
"""str: Constant string used to describe sliding NIS method."""

FADING_MEMORY_NIS_LABEL = 'fading_memory_nis'
"""str: Constant string used to describe fading memory NIS method."""


def nisFactory(method):
    """Build a dynamics propagation noise covariance matrix.

    Args:
        method (``str``): the function used to generate the noise covariance

    Note:
        Valid options for "method" argument:
        'standard_nis'
        'sliding_nis'
        'fading_memory_nis'

    Raises:
        ValueError: raised if given an invalid "method" argument

    Returns:
        NIS
    """
    if method.name == NO_SETTING:
        return None
    elif method.name == STANDARD_NIS_LABEL:
        nis_class = Nis(method.maneuver_gate_val)
    elif method.name == SLIDING_NIS_LABEL:
        nis_class = SlidingNis(method.maneuver_gate_val, method.parameters['window'])
    elif method.name == FADING_MEMORY_NIS_LABEL:
        nis_class = FadingMemoryNis(method.maneuver_gate_val)
    else:
        raise ValueError(method)

    return nis_class
