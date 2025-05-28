"""Defines the :class:`.SequentialFilter` base class to formalize an interface for sequential filtering algorithms."""

from __future__ import annotations

# Standard Library Imports
import logging
from abc import ABC, abstractmethod
from enum import Enum, Flag, auto
from typing import TYPE_CHECKING

# Third Party Imports
from numpy import array, fabs
from scipy.linalg import norm

# Local Imports
from ..common.behavioral_config import BehavioralConfig
from ..data import getDBConnection
from ..data.queries import fetchTruthByJDEpoch
from .results import (
    FilterResult,
    SeqFilterForecastResult,
    SeqFilterPredictResult,
    SeqFilterUpdateResult,
)

if TYPE_CHECKING:
    # Standard Library Imports
    from typing import Any

    # Third Party Imports
    from numpy import ndarray

    # Local Imports
    from ..data.observation import Observation
    from ..dynamics.dynamics_base import Dynamics
    from ..dynamics.integration_events import ScheduledEventType
    from ..physics.time.stardate import ScenarioTime
    from ..scenario.config.estimation_config import SequentialFilterConfig
    from .maneuver_detection import ManeuverDetection


class FilterFlag(Flag):
    """Flags for tracking filter events."""

    NONE = 0
    MANEUVER_DETECTION = auto()
    ADAPTIVE_ESTIMATION_START = auto()
    ADAPTIVE_ESTIMATION_CLOSE = auto()
    INITIAL_ORBIT_DETERMINATION_START = auto()


class EstimateSource(str, Enum):
    """Estimate source definitions."""

    INITIALIZATION = "Initialization"
    """``str``: An estimate source due to internal filter initialization."""

    INTERNAL_PROPAGATION = "Propagation"
    """``str``: An estimate source due to internal filter propagation."""

    INTERNAL_OBSERVATION = "Observation"
    """``str``: An estimate source due to internal filter measurement update."""


class SequentialFilter(ABC):
    r"""Defines common interface for a recursive sequential state estimation filter.

    Most methods are abstract, so implementers can define their custom algorithms, but users can
    rely on a common interface. This class relies on interactions with a containing
    :class:`.EstimateAgent`, and references to :class:`.SensingAgent` to properly work.

    .. rubric:: Terminology

    The terminology used here refers to the **a** **priori** state estimate and error
    covariance as :attr:`.pred_x` and :attr:`.pred_p`, respectively, and the **a**
    **posteriori** state estimate and error covariance as :attr:`.est_x` and :attr:`.est_p`,
    respectively. For a more formalized definition of these terms and their rigorous
    derivations, see :cite:p:`bar-shalom_2001_estimation` or :cite:p:`crassidis_2012_optest`.

    .. rubric:: Notation

    - :math:`x` refers to the state estimate vector
    - :math:`P` refers to the error covariance matrix
    - :math:`y` refers to the measurement vector
    - :math:`N` is defined as the number of dimensions of the state estimate, :math:`x`, which is constant
    - :math:`M` is defined as the number of dimensions of the measurement, :math:`y`, which can vary with time.
    - :math:`k` is defined as the current timestep of the simulation
    - :math:`k+1` is defined as the future timestep at which the filter is predicting/estimating

    Attributes:
        dynamics (:class:`.Dynamics`): dynamics model that propagates the estimate forward in time.
        x_dim (``int``): the dimension size of the state estimate.
        pred_x (``ndarray``): :math:`N\times 1` predicted (**priori**) state estimate at :math:`k+1`.
        est_x (``ndarray``): :math:`N\times 1` estimated (**posteriori**) state estimate at :math:`k+1`.
        est_p (``ndarray``): :math:`N\times 1` estimated (**posteriori**) error covariance at :math:`k+1`.
        nis (``float``): normalized innovations squared values. Defines a chi-squared distributed
            sequence with :math:`M` degrees of freedom. This allows for simple checking of filter
            consistency and modeling errors.
        source (``str``): Variable determining whether observations were used during an update
            step. Acceptable values:

            1. :py:data:`'Propagation'` = no observations were used.
            2. :py:data:`'Observation'` = at least one observation was used.

        innov_cvr (``ndarray``): :math:`M\times M` innovation (aka measurement prediction) covariance
            matrix. Defines the "accuracy" of the measurements.
        cross_cvr (``ndarray``): :math:`N\times M` cross covariance matrix. Defines the covariance
            between the state and measurement.
        innovation (``ndarray``): :math:`M\times 1` innovation (aka measurement residual) vector. Defines
            the residual error between the true measurement and the mean predicted measurement.
        is_angular (``ndarray``): :math:`M\times 1` integer vector describing which measurements are angles.
            This allows proper handling of angle measurements when calculating the
            measurement mean and residuals vectors. The following values are valid:

            - `1` for a non-angular measurement, no special treatment is needed
            - `2` for an angular measurement valid in :math:`[0, 2\pi)`
            - `3` for an angular measurement valid in :math:`(-\pi, \pi]`
        extra_parameters (``dict``): parameters specific for derived filter objects, saved for easy, generic access

    References:
        #. :cite:t:`bar-shalom_2001_estimation`
        #. :cite:t:`crassidis_2012_optest`
    """

    def __init__(  # noqa: PLR0913
        self,
        tgt_id: int,
        time: ScenarioTime,
        est_x: ndarray,
        est_p: ndarray,
        dynamics: Dynamics,
        maneuver_detection: ManeuverDetection | None,
        initial_orbit_determination: bool,
        adaptive_estimation: bool,
        extra_parameters: dict[str, Any] | None = None,
    ):
        r"""Initialize a generic sequential filter class.

        Args:
            tgt_id (``int``): unique ID of the target associated with this filter object
            time (:class:`.ScenarioTime`): value for the initial time (sec)
            est_x (``ndarray``): :math:`N\times 1` initial state estimate
            est_p (``ndarray``): :math:`N\times N` initial covariance
            dynamics (:class:`.Dynamics`): dynamics object associated with the filter's target
            maneuver_detection (:class:`.ManeuverDetection`): ManeuverDetection associated with the filter
            initial_orbit_determination (``bool``, optional): Indicator that IOD can be flagged by the filter
            adaptive_estimation (``bool``, optional): Indicator that adaptive estimation can be flagged by the filter
            extra_parameters (``dict``, optional): extra arguments for derived classes, for allowing dynamic
                creation from within this class
        """
        self.logger = logging.getLogger(f"resonaate.est.{self.__class__.__name__}.{tgt_id}")

        # Define the filter's scope/behavior
        self.dynamics: Dynamics = dynamics
        self.target_id: int = tgt_id
        self.time: ScenarioTime = time

        # Initialize key variables used in filter process
        self.x_dim: int = len(est_x)

        # Maneuver detection attributes
        self.maneuver_metric: float | None = None
        self.maneuver_detected: bool = False
        self.maneuver_detection: ManeuverDetection = maneuver_detection

        # Extra parameters for subclasses
        self.extra_parameters: dict[str, Any] | None = extra_parameters

        # Main estimation products, used as outputs of the filter class
        self.est_x: ndarray = est_x
        self.pred_x = array([])
        self.source: EstimateSource = EstimateSource.INITIALIZATION

        # Check that IOD and MMAE are both not set.
        if initial_orbit_determination and adaptive_estimation:
            raise ValueError("IOD & MMAE cannot be used at the same time")

        # MMAE products
        self.true_y = array([])
        self.adaptive_estimation: bool = adaptive_estimation

        # Orbit Determination products
        self.initial_orbit_determination: bool = initial_orbit_determination

        # Intermediate values, used for checking statistical consistency & simplifying equations
        self.nis = array([])
        self.r_matrix = array([])
        self.innovation = array([])
        self.is_angular = array([])

        # Set filter flags to empty
        self._flags = FilterFlag.NONE

    @classmethod
    @abstractmethod
    def fromConfig(
        cls,
        config: SequentialFilterConfig,
        tgt_id: int,
        time: ScenarioTime,
        est_x: ndarray,
        est_p: ndarray,
        dynamics: Dynamics,
        maneuver_detection: ManeuverDetection,
        *args,
        **kwargs,
    ) -> SequentialFilter:
        """Build a :class:`.SequentialFilter` object for target state estimation.

        Args:
            config (:class:`.SequentialFilterConfig`): describes the filter to be built
            tgt_id (``int``): unique ID of the associated target agent
            time (:class:`.ScenarioTime`): initial time of scenario
            est_x (``ndarray``): 6x1, initial state estimate
            est_p (``ndarray``): 6x6, initial error covariance matrix
            dynamics (:class:`.Dynamics`): dynamics object to propagate estimate
            maneuver_detection (.ManeuverDetection): ManeuverDetection associated with the filter
            args (``list[Unknown]``): a list of other arguments; may be used by subclasses
            kwargs (``dict[str, Unknown]``): a dictionary of other arguments; may be used by subclasses

        Returns:
            :class:`.SequentialFilter`: constructed filter object
        """
        raise NotImplementedError

    @abstractmethod
    def predict(
        self,
        final_time: ScenarioTime,
        scheduled_events: list[ScheduledEventType] | None = None,
    ):
        """Propagate the state estimate and error covariance with uncertainty.

        Args:
            final_time (:class:`.ScenarioTime`): time to propagate to
            scheduled_events (``list``, optional): scheduled events to apply during propagation which
                can either be implemented :class:`.ContinuousStateChangeEvent` or
                :class:`.DiscreteStateChangeEvent` objects.
        """
        raise NotImplementedError

    @abstractmethod
    def forecast(self, observations: list[Observation]):
        """Update the error covariance with observations.

        Args:
            observations (``list``): :class:`.Observation` objects associated with the filter step
        """
        raise NotImplementedError

    @abstractmethod
    def update(self, observations: list[Observation]):
        """Update the state estimate with observations.

        Args:
            observations (``list``): :class:`.Observation` objects associated with the filter step
        """
        raise NotImplementedError

    def checkManeuverDetection(self):
        """Performs maneuver detection, if configured and kicks off adaptive estimation, if configured."""
        if self.maneuver_detection is None:
            return

        self.maneuver_detected = self.maneuver_detection(self.innovation, self.innov_cvr)
        if not self.maneuver_detected:
            return

        self.flags |= FilterFlag.MANEUVER_DETECTION
        self.maneuver_metric = self.maneuver_detection.metric
        if self.adaptive_estimation and FilterFlag.ADAPTIVE_ESTIMATION_START not in self.flags:
            self.flags |= FilterFlag.ADAPTIVE_ESTIMATION_START
        if (
            self.initial_orbit_determination
            and FilterFlag.INITIAL_ORBIT_DETERMINATION_START not in self.flags
        ):
            self.flags |= FilterFlag.INITIAL_ORBIT_DETERMINATION_START

    def getPredictionResult(self) -> SeqFilterPredictResult:
        """Compile result message for a predict step.

        Returns:
            Filter results from the 'predict' step.
        """
        return SeqFilterPredictResult.fromFilter(self)

    def getForecastResult(self) -> SeqFilterForecastResult:
        """Compile result message for a forecast step.

        Returns:
            Filter results from the 'forecast' step.
        """
        return SeqFilterForecastResult.fromFilter(self)

    def getUpdateResult(self) -> SeqFilterUpdateResult:
        """Compile result message for an update step.

        Returns:
            Filter results from the 'update' step.
        """
        return SeqFilterUpdateResult.fromFilter(self)

    def applyFilterResult(self, filter_result: FilterResult):
        """Set the corresponding values of this filter based on a filter step result.

        Args:
            filter_result: updated attributes of a filter after an step was processed.
        """
        filter_result.apply(self)

    def propagate(
        self,
        final_time: ScenarioTime,
        scheduled_events: list[ScheduledEventType] | None = None,
    ):
        r"""Enable a filter to propagate the state forward in time like a :class:`.Dynamics` object.

        Args:
            final_time (:class:`.ScenarioTime`): value for the time of the propagated state (sec)
            scheduled_events (``list``, optional): scheduled events to apply during propagation which
                can either be implemented :class:`.ContinuousStateChangeEvent` or
                :class:`.DiscreteStateChangeEvent` objects.
        """
        raise NotImplementedError

    def _debugChecks(self, observations: list[Observation]):
        """Debugging checks if flags are set to do so."""
        # Check if error inflation is too large
        if BehavioralConfig.getConfig().debugging.EstimateErrorInflation:
            database = getDBConnection()
            truth = fetchTruthByJDEpoch(database, self.target_id, observations[0].julian_date)
            tol_km = 5  # Estimate inflation error tolerance (km)
            pred_error = fabs(norm(truth[:3] - self.pred_x[:3]))
            est_error = fabs(norm(truth[:3] - self.est_x[:3]))

            # If error increase is larger than desired log the debug information
            if est_error > pred_error + tol_km:
                msg = (
                    f"EstimateAgent error inflation occurred: {self.target_id} at {self.time} sec",
                )
                self.logger.warning(msg)

    @property
    def flags(self):
        """:class:.`FilterDebugFlag`: Returns the current filter flags."""
        return self._flags

    @flags.setter
    def flags(self, new_flags: FilterFlag):
        """Set the filter flags attribute."""
        if not isinstance(new_flags, FilterFlag):
            raise TypeError(new_flags)

        self._flags = new_flags
