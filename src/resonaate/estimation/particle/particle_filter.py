"""Defines the :class:`.ParticleFilter` base class to formalize an interface for sequential filtering algorithms."""

from __future__ import annotations

# Standard Library Imports
from enum import Flag, auto
from typing import TYPE_CHECKING

# Third Party Imports
from numpy import array

# Local Imports
from ..results import (
    ParticleFilterForecastResult,
    ParticleFilterPredictResult,
    ParticleFilterUpdateResult,
)
from ..sequential_filter import SequentialFilter

if TYPE_CHECKING:
    # Standard Library Imports
    from typing import Any

    # Third Party Imports
    from numpy import ndarray

    # Local Imports
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


class ParticleFilter(SequentialFilter):
    r"""Defines common interface for a recursive particle-based state estimation filter.

    Most methods are abstract, so implementers can define their custom algorithms, but users can
    rely on a common interface. This class relies on interactions with a containing
    :class:`.EstimateAgent`, and references to :class:`.SensingAgent` to properly work.

    .. rubric:: Terminology

    The terminology used here refers to the **a** **priori** state estimate and error
    covariance as :attr:`.pred_x` and :attr:`.pred_p`, respectively, and the **a**
    **posteriori** state estimate and error covariance as :attr:`.est_x` and :attr:`.est_p`,
    respectively.

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
        source (``str``): Variable determining whether observations were used during an update
            step. Acceptable values:

            1. :py:data:`'Propagation'` = no observations were used.
            2. :py:data:`'Observation'` = at least one observation was used.

        extra_parameters (``dict``): parameters specific for derived filter objects, saved for easy, generic access

    References:
        TBD
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

        self.population: ndarray = array([])
        self.station_keeping = None

    def getPredictionResult(self) -> ParticleFilterPredictResult:
        """Compile result message for a predict step.

        Returns:
            Filter results from the 'predict' step.
        """
        return ParticleFilterPredictResult.fromFilter(self)

    def getForecastResult(self) -> ParticleFilterForecastResult:
        """Compile result message for a forecast step.

        Returns:
            Filter results from the 'forecast' step.
        """
        return ParticleFilterForecastResult.fromFilter(self)

    def getUpdateResult(self) -> ParticleFilterUpdateResult:
        """Compile result message for an update step.

        Returns:
            Filter results from the 'update' step.
        """
        return ParticleFilterUpdateResult.fromFilter(self)

    def propagate(
        self,
        final_time: ScenarioTime,
        scheduled_events: list[ScheduledEventType] | None = None,
    ) -> ndarray:
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
        return self.pred_x
