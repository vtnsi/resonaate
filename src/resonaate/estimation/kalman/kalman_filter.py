"""Defines the :class:`.SequentialFilter` base class to formalize an interface for sequential filtering algorithms."""

from __future__ import annotations

# Standard Library Imports
from enum import Flag, auto
from typing import TYPE_CHECKING

# Third Party Imports
from numpy import array

# Local Imports
from ..sequential_filter import SequentialFilter

if TYPE_CHECKING:
    # Standard Library Imports
    from typing import Any

    # Third Party Imports
    from numpy import ndarray

    # Local Imports
    from ...dynamics.dynamics_base import Dynamics
    from ...physics.time.stardate import ScenarioTime
    from ..maneuver_detection import ManeuverDetection


class FilterFlag(Flag):
    """Flags for tracking filter events."""

    NONE = 0
    MANEUVER_DETECTION = auto()
    ADAPTIVE_ESTIMATION_START = auto()
    ADAPTIVE_ESTIMATION_CLOSE = auto()
    INITIAL_ORBIT_DETERMINATION_START = auto()


class KalmanFilter(SequentialFilter):
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
        super().__init__(
            tgt_id,
            time,
            est_x,
            est_p,
            dynamics,
            maneuver_detection,
            initial_orbit_determination,
            adaptive_estimation,
            extra_parameters,
        )

        self.q_matrix: ndarray = q_matrix

        # Main estimation products, used as outputs of the filter class
        self.est_p: ndarray = est_p
        self.pred_p = array([])

        # Intermediate values, used for checking statistical consistency & simplifying equations
        self.innov_cvr = array([])
        self.cross_cvr = array([])
        self.kalman_gain = array([])
        self.mean_pred_y = array([])
