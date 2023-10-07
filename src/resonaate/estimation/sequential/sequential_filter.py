"""Defines the :class:`.SequentialFilter` base class to formalize an interface for sequential filtering algorithms."""
from __future__ import annotations

# Standard Library Imports
import logging
from abc import ABC, abstractmethod
from enum import Flag, auto
from typing import TYPE_CHECKING

# Third Party Imports
from numpy import array, fabs
from scipy.linalg import norm

# Local Imports
from ...common.behavioral_config import BehavioralConfig
from ...data import getDBConnection
from ...data.queries import fetchTruthByJDEpoch
from ..debug_utils import checkThreeSigmaObs, logFilterStep

if TYPE_CHECKING:
    # Standard Library Imports
    from typing import Any

    # Third Party Imports
    from numpy import ndarray

    # Local Imports
    from ...data.observation import Observation
    from ...dynamics.dynamics_base import Dynamics
    from ...dynamics.integration_events import ScheduledEventType
    from ...physics.time.stardate import ScenarioTime
    from ..maneuver_detection import ManeuverDetection


class FilterFlag(Flag):
    """Flags for tracking filter events."""

    NONE = 0
    MANEUVER_DETECTION = auto()
    ADAPTIVE_ESTIMATION_START = auto()
    ADAPTIVE_ESTIMATION_CLOSE = auto()
    INITIAL_ORBIT_DETERMINATION_START = auto()


class SequentialFilter(ABC):  # pylint: disable=too-many-instance-attributes
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
        q_matrix (``ndarray``): :math:`N\times N` process noise covariance matrix. Defines the dynamics
            model uncertainty assumed by the filter.
        pred_x (``ndarray``): :math:`N\times 1` predicted (**priori**) state estimate at :math:`k+1`.
        pred_p (``ndarray``): :math:`N\times N` predicted (**priori**) error covariance at :math:`k+1`.
        est_x (``ndarray``): :math:`N\times 1` estimated (**posteriori**) state estimate at :math:`k+1`.
        est_p (``ndarray``): :math:`N\times 1` estimated (**posteriori**) error covariance at :math:`k+1`.
        nis (``float``): normalized innovations squared values. Defines a chi-squared distributed
            sequence with :math:`M` degrees of freedom. This allows for simple checking of filter
            consistency and modeling errors.
        source (``str``): Variable determining whether observations were used during an update
            step. Acceptable values:

            1. :py:data:`'Propagation'` = no observations were used.
            2. :py:data:`'Observation'` = at least one observation was used.

        r_matrix (``ndarray``): :math:`M\times M` measurement error covariance matrix at :math:`k+1`. Most
            literature assumes that this is defined as constant/unchanging matrix, but this
            work allows it to change with varying numbers of sensors. This allows for disparate
            observations from many different types of sensors to contribute information, which is
            more flexible/realistic. This is done by concatenating individual measurement noise
            matrices of the observing sensors on every timestep, which means the size, :math:`M`, varies
            with time.
        innov_cvr (``ndarray``): :math:`M\times M` innovation (aka measurement prediction) covariance
            matrix. Defines the "accuracy" of the measurements.
        cross_cvr (``ndarray``): :math:`N\times M` cross covariance matrix. Defines the covariance
            between the state and measurement.
        kalman_gain (``ndarray``): :math:`N\times M` Kalman gain matrix. Defines the relative importance
            of the state prediction variance vs. innovation variance.
        mean_pred_y (``ndarray``): :math:`M\times 1` predicted mean measurement vector. Defines mean
            value of the predicted measurement(s) based on the predicted state estimate.
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

    INTERNAL_PROPAGATION_SOURCE = "Propagation"
    """``str``: Constant string for an estimate source due to internal filter propagation."""

    INTERNAL_OBSERVATION_SOURCE = "Observation"
    """``str``: Constant string for an estimate source due to internal filter measurement update."""

    def __init__(  # noqa: PLR0913
        self,
        tgt_id: int,
        time: ScenarioTime,
        est_x: ndarray,
        est_p: ndarray,
        dynamics: Dynamics,
        q_matrix: ndarray,
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
            q_matrix (``ndarray``): dynamics error covariance matrix
            maneuver_detection (:class:`.ManeuverDetection`): ManeuverDetection associated with the filter
            initial_orbit_determination (``bool``, optional): Indicator that IOD can be flagged by the filter
            adaptive_estimation (``bool``, optional): Indicator that adaptive estimation can be flagged by the filter
            extra_parameters (``dict``, optional): extra arguments for derived classes, for allowing dynamic
                creation from within this class
        """
        self._logger = logging.getLogger("resonaate")

        # Define the filter's scope/behavior
        self.dynamics = dynamics
        self.target_id = tgt_id
        self.time = time

        # Initialize key variables used in filter process
        self.x_dim = len(q_matrix)
        self.q_matrix = q_matrix

        # Maneuver detection attributes
        self.maneuver_metric: float | None = None
        self.maneuver_detected = False
        self.maneuver_detection = maneuver_detection

        # Extra parameters for subclasses
        self.extra_parameters = extra_parameters

        # Main estimation products, used as outputs of the filter class
        self.est_x = est_x
        self.est_p = est_p
        self.pred_x = array([])
        self.pred_p = array([])
        self.source: str | None = "Initialization"

        # MMAE products
        self.true_y = array([])
        self.adaptive_estimation = adaptive_estimation

        # Orbit Determination products
        self.initial_orbit_determination = initial_orbit_determination

        # Intermediate values, used for checking statistical consistency & simplifying equations
        self.nis = array([])
        self.r_matrix = array([])
        self.innov_cvr = array([])
        self.cross_cvr = array([])
        self.kalman_gain = array([])
        self.mean_pred_y = array([])
        self.innovation = array([])
        self.is_angular = array([])

        # Set filter flags to empty
        self._flags = FilterFlag.NONE

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
        if self.maneuver_detection:
            self.maneuver_detected = self.maneuver_detection(self.innovation, self.innov_cvr)

        if self.maneuver_detected:
            self.flags |= FilterFlag.MANEUVER_DETECTION
            self.maneuver_metric = self.maneuver_detection.metric
            if self.adaptive_estimation and FilterFlag.ADAPTIVE_ESTIMATION_START not in self.flags:
                self.flags |= FilterFlag.ADAPTIVE_ESTIMATION_START
            if (
                self.initial_orbit_determination
                and FilterFlag.INITIAL_ORBIT_DETERMINATION_START not in self.flags
            ):
                self.flags |= FilterFlag.INITIAL_ORBIT_DETERMINATION_START

    def getPredictionResult(self) -> dict[str, Any]:
        """Compile result message for a predict step.

        Returns:
            ``dict``: message with predict information
        """
        return {
            "time": self.time,
            "est_x": self.est_x,
            "est_p": self.est_p,
            "pred_x": self.pred_x,
            "pred_p": self.pred_p,
        }

    def getForecastResult(self) -> dict[str, Any]:
        """Compile result message for a forecast step.

        Returns:
            ``dict``: message with forecast information
        """
        return {
            "is_angular": self.is_angular,
            "mean_pred_y": self.mean_pred_y,
            "r_matrix": self.r_matrix,
            "cross_cvr": self.cross_cvr,
            "innov_cvr": self.innov_cvr,
            "kalman_gain": self.kalman_gain,
            "est_p": self.est_p,
        }

    def getUpdateResult(self) -> dict[str, Any]:
        """Compile result message for an update step.

        Returns:
            ``dict``: message with update information
        """
        result = self.getForecastResult()
        result.update(
            {
                "est_x": self.est_x,
                "innovation": self.innovation,
                "nis": self.nis,
                "source": self.source,
                "maneuver_metric": self.maneuver_metric,
                "maneuver_detected": self.maneuver_detected,
            }
        )
        return result

    def updateFromAsyncResult(self, async_result: dict[str, Any]):
        """Set the corresponding values of this filter based on a filter async job result.

        Args:
            async_result (``dict``): updated attributes of a filter after an async job.
        """
        for key, value in async_result.items():
            setattr(self, key, value)

    def propagate(
        self,
        final_time: ScenarioTime,
        scheduled_events: list[ScheduledEventType] | None = None,
    ) -> tuple[ndarray, ndarray]:
        r"""Enable a filter to propagate the state forward in time like a :class:`.Dynamics` object.

        Args:
            final_time (:class:`.ScenarioTime`): value for the time of the propagated state (sec)
            scheduled_events (``list``, optional): scheduled events to apply during propagation which
                can either be implemented :class:`.ContinuousStateChangeEvent` or
                :class:`.DiscreteStateChangeEvent` objects.

        Returns:
            - :math:`N\times 1` propagated state vector
            - :math:`N\times N` propagated covariance matrix
        """
        self.predict(final_time, scheduled_events=scheduled_events)
        return self.pred_x, self.pred_p

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
            if est_error > pred_error + tol_km:  # pylint: disable=consider-using-assignment-expr
                file_name = logFilterStep(self, observations, truth)
                msg = f"EstimateAgent error inflation occurred:\n\t{file_name}"
                self._logger.warning(msg)

        if BehavioralConfig.getConfig().debugging.ThreeSigmaObs:
            filenames = checkThreeSigmaObs(observations, sigma=3)
            msg = "Made bad observation, debugging info:\n\t"
            for filename in filenames:
                self._logger.warning(msg + f"{filename}")

    @property
    def logger(self):
        """Returns the logger."""
        return self._logger

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
