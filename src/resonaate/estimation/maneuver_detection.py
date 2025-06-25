"""Defines statistical functions and tests for analyzing filtering algorithms."""

from __future__ import annotations

# Standard Library Imports
from abc import ABCMeta, abstractmethod
from collections import deque
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Union

# Local Imports
from ..common.logger import resonaateLogError
from ..physics.statistics import chiSquareQuadraticForm, oneSidedChiSquareTest

if TYPE_CHECKING:
    # Third Party Imports
    from numpy import ndarray

    # Local Imports
    from ..scenario.config.estimation_config import ManeuverDetectionConfig

TestType = Callable[[float, float, float, Union[float, None]], bool]


class ManeuverDetection(metaclass=ABCMeta):
    r"""Abstract class that encapsulates methods of detecting maneuvers."""

    def __init__(self, threshold: float):
        r"""Initialize maneuver detection class.

        Args:
            threshold (``float``): value used in statistical hypothesis testing. This value is
                assumed to be the upper tail probability, or the null hypothesis probability,
                which means the expected confidence interval that a maneuver does **not** occur.
        """
        self.threshold = threshold
        self.metric = None

    @classmethod
    @abstractmethod
    def fromConfig(cls, config: ManeuverDetectionConfig) -> ManeuverDetection:
        """Build a maneuver detection class based on specified `config`.

        Args:
            config (:class:`.ManeuverDetectionConfig`): Configuration to build maneuver detection
                method from.

        Returns:
            :class:`.ManeuverDetection`: Maneuver detection method build from specified `config`.
        """
        raise NotImplementedError

    @abstractmethod
    def __call__(self, *args: Any, test: TestType = oneSidedChiSquareTest, **kwargs: Any) -> bool:
        r"""Implements the ``Callable`` protocol/interface, so the class can be used like a function.

        Args:
            args (Any): variable set of positional arguments.
            test (``Callable``, optional): the hypothesis testing function used to determine
                whether a maneuver occurred or not. Defaults to :func:`.oneSidedChiSquareTest`.
            kwargs (Any): variable set of keyword arguments.

        Returns:
            ``bool``: ``True`` if the tests fails, which means a maneuver is detected, and
                ``False`` if the test passes, for the nominal case.
        """
        return NotImplemented


class StandardNis(ManeuverDetection):
    r"""Normalized Innovations Squared (NIS) class.

    This maneuver detection technique implements the normalized innovations squared value which is
    by definition a chi-square random variable, :math:`\chi^{2}_{n} (\alpha)`, with :math:`n`
    degrees of freedom, and tail probability of :math:`\alpha`. This value is then subjected to a
    hypothesis test where the null hypothesis is that a maneuver has not occurred (the NIS lie
    within the chi-square bounds). The NIS of a Kalman filter is defined as

    .. math::

        \epsilon_{\nu}(k) &= \nu(k)^{T} S_{\nu}(k)^{-1} \nu(k) \\
        \epsilon_{\nu} & \sim \chi^{2}_{n_z} \\

    where :math:`\nu` is the measurement residuals vector, :math:`S_{\nu}` is the
    innovations covariance matrix, :math:`k` is the
    current timestep, and :math:`n_z` is the filter's observation-space dimension.

    References:
        :cite:t:`bar-shalom_2001_estimation`, Section 11.2.2, Eqn 11.2.2-1 & 11.2.2-2
    """

    @classmethod
    def fromConfig(cls, config: ManeuverDetectionConfig) -> ManeuverDetection:
        """Build a maneuver detection class based on specified `config`.

        Args:
            config (:class:`.ManeuverDetectionConfig`): Configuration to build maneuver detection
                method from.

        Returns:
            :class:`.ManeuverDetection`: Maneuver detection method build from specified `config`.
        """
        return cls(config.threshold)

    def __call__(
        self,
        residual: ndarray,
        innov_cvr: ndarray,
        *args: Any,
        test: TestType = oneSidedChiSquareTest,
        **kwargs: Any,
    ) -> bool:
        r"""Calculate Standard Nis.

        Args:
            residual (``ndarray``): :math:`N_z\times 1` measurement residual vector.
            innov_cvr (``ndarray``): innovation covariance matrix.
            test (``Callable``, optional): the hypothesis testing function used to determine
                whether a maneuver occurred or not. Defaults to :func:`.oneSidedChiSquareTest`.
            args (Any): variable set of positional arguments.
            kwargs (Any): variable set of keyword arguments.

        Returns:
            ``bool``: ``True`` if the tests fails, which means a maneuver is detected, and
                ``False`` if the test passes, for the nominal case.
        """
        dof = residual.shape[0]
        self.metric = chiSquareQuadraticForm(residual, innov_cvr)
        return not test(self.metric, self.threshold, dof)


class SlidingNis(StandardNis):
    r"""Calculate the sliding window normalized innovations squared of a filter update.

    This maneuver detection technique uses the NIS from the previous :math:`s` time steps by
    averaging them over time:

    .. math::

        \epsilon_{\nu}^{s}(k) &= \sum_{j=k-s+1}^{k}\epsilon_{\nu}(j) \\
        \epsilon_{\nu}^{s} & \sim \chi^{2}_{sn_z} \\

    which is chi-square with :math:`sn_z` degrees of freedom.

    See Also:
        :class:`.StandardNis` for the definition of NIS (:math:`\epsilon_{\nu}`) and using
        hypothesis testing.

    References:
        :cite:t:`bar-shalom_2001_estimation`, Section 11.2.2, Eqn 11.2.2-3 & 11.2.2-4
    """

    def __init__(self, threshold: float, window_size: int = 4):
        r"""Initialize a sliding NIS maneuver detection class.

        Args:
            threshold (``float``): value used in statistical hypothesis testing. This value is
                assumed to be the upper tail probability, or the null hypothesis probability,
                which means the expected confidence interval that a maneuver does **not** occur.
            window_size (``int``): length of the sliding window used to "average" NIS over
                multiple timesteps. Defaults to 4.
        """
        super().__init__(threshold)
        if window_size <= 0:
            msg = f"Invalid value for SlidingNis discount factor, window_size: {window_size}"
            resonaateLogError(msg)
            raise ValueError(msg)
        self.window_size = window_size
        self.nis_list = deque(maxlen=window_size)
        self.dim_list = deque(maxlen=window_size)

    @classmethod
    def fromConfig(cls, config: ManeuverDetectionConfig) -> ManeuverDetection:
        """Build a maneuver detection class based on specified `config`.

        Args:
            config (:class:`.ManeuverDetectionConfig`): Configuration to build maneuver detection
                method from.

        Returns:
            :class:`.ManeuverDetection`: Maneuver detection method build from specified `config`.
        """
        return cls(config.threshold, window_size=config.window_size)

    def __call__(
        self,
        residual: ndarray,
        innov_cvr: ndarray,
        *args: Any,
        test: TestType = oneSidedChiSquareTest,
        **kwargs: Any,
    ) -> bool:
        r"""Calculate Sliding Nis.

        Args:
            residual (``ndarray``): :math:`N_z\times 1` measurement residual vector.
            innov_cvr (``ndarray``): innovation covariance matrix.
            test (``Callable``, optional): the hypothesis testing function used to determine
                whether a maneuver occurred or not. Defaults to :func:`.oneSidedChiSquareTest`.
            args (Any): variable set of positional arguments.
            kwargs (Any): variable set of keyword arguments.

        Returns:
            ``bool``: ``True`` if the tests fails, which means a maneuver is detected, and
                ``False`` if the test passes, for the nominal case.
        """
        self.nis_list.append(chiSquareQuadraticForm(residual, innov_cvr))
        self.dim_list.append(residual.shape[0])
        dof = sum(self.dim_list)
        self.metric = sum(self.nis_list)
        return not test(self.metric, self.threshold, dof)


class FadingMemoryNis(StandardNis):
    r"""Calculate the fading memory average normalized innovations squared of a filter update.

    This maneuver detection technique discounts previous NIS values by a multiplicative factor:

    .. math::

        \epsilon_{\nu}^{\delta}(k) &= \delta\epsilon_{\nu}^{\delta}(k - 1) + \epsilon_{\nu}(k) \\
        \epsilon_{\nu}^{\delta} & \sim \frac{1}{1+\delta}\chi^{2}_{n_{\delta}} \\

    where :math:`0<\delta<1` is the exponential discount factor. This metric is chi-square with
    :math:`n_{\delta} = n_z\frac{1+\delta}{1-\delta}` degrees of freedom. This uses the first and
    second moment-matching approximation.

    See Also:
        :class:`.StandardNis` for the definition of NIS (:math:`\epsilon_{\nu}`) and using
        hypothesis testing.

    References:
        :cite:t:`bar-shalom_2001_estimation`, Section 11.2.2, Eqn 11.2.2-5, 11.2.2-9, & 11.2.2-10
    """

    def __init__(self, threshold: float, delta: float = 0.8):
        r"""Initialize a fading memory NIS maneuver detection class.

        Args:
            threshold (``float``): value used in statistical hypothesis testing. This value is
                assumed to be the upper tail probability, or the null hypothesis probability,
                which means the expected confidence interval that a maneuver does **not** occur.
            delta (``float``): scale by which previous NIS values are weighted,
                :math:`0 < \delta < 1`. Defaults to 0.8.
        """
        super().__init__(threshold)
        if delta <= 0 or delta >= 1:
            msg = f"Invalid value for FadingMemoryNis discount factor, delta: {delta}"
            resonaateLogError(msg)
            raise ValueError(msg)
        self.delta = delta
        self.prior_nis = 0.0
        # Help track time-varying observation dim
        self.total_dim = 0
        self.total = 0

    @classmethod
    def fromConfig(cls, config: ManeuverDetectionConfig) -> ManeuverDetection:
        """Build a maneuver detection class based on specified `config`.

        Args:
            config (:class:`.ManeuverDetectionConfig`): Configuration to build maneuver detection
                method from.

        Returns:
            :class:`.ManeuverDetection`: Maneuver detection method build from specified `config`.
        """
        return cls(config.threshold, delta=config.delta)

    def __call__(
        self,
        residual: ndarray,
        innov_cvr: ndarray,
        *args: Any,
        test: TestType = oneSidedChiSquareTest,
        **kwargs: Any,
    ) -> bool:
        r"""Calculate Fading Memory Nis.

        Args:
            residual (``ndarray``): :math:`N_z\times 1` measurement residual vector.
            innov_cvr (``ndarray``): innovation covariance matrix.
            test (``Callable``, optional): the hypothesis testing function used to determine
                whether a maneuver occurred or not. Defaults to :func:`.oneSidedChiSquareTest`.
            args (Any): variable set of positional arguments.
            kwargs (Any): variable set of keyword arguments.

        Returns:
            ``bool``: ``True`` if the tests fails, which means a maneuver is detected, and
                ``False`` if the test passes, for the nominal case.
            ``float``: the metric used in the maneuver detection test.
        """
        # Update the current average dim to account for time-varying observation dim
        dim = residual.shape[0]
        self.total += 1
        self.total_dim += dim
        avg_dim = self.total_dim / self.total
        # Moment-matched DOF
        dof = avg_dim * (1 + self.delta) / (1 - self.delta)
        self.prior_nis = self.delta * self.prior_nis + chiSquareQuadraticForm(residual, innov_cvr)
        # Moment-match metric value
        self.metric = self.prior_nis * (1 + self.delta)
        return not test(self.metric, self.threshold, dof)
