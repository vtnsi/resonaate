"""Contains all classes and functions related to estimation theory.

This includes Kalman filter classes, statistical tests, and debugging utility functions.
"""
from __future__ import annotations

# Standard Library Imports
from copy import deepcopy
from typing import TYPE_CHECKING

# Local Imports
from .adaptive.adaptive_filter import AdaptiveFilter
from .adaptive.gpb1 import GeneralizedPseudoBayesian1
from .adaptive.smm import StaticMultipleModel
from .maneuver_detection import FadingMemoryNis, ManeuverDetection, SlidingNis, StandardNis
from .sequential.sequential_filter import SequentialFilter
from .sequential.unscented_kalman_filter import UnscentedKalmanFilter

# Type Checking Imports
if TYPE_CHECKING:
    # Standard Library Imports
    from typing import Dict, Tuple

    # Third Party Imports
    from numpy import ndarray

    # Local Imports
    from ..dynamics.dynamics_base import Dynamics
    from ..physics.time.stardate import ScenarioTime
    from ..scenario.config.estimation_config import (
        AdaptiveEstimationConfig,
        ManeuverDetectionConfig,
        SequentialFilterConfig,
    )


VALID_ESTIMATE_SOURCE_LABELS: Tuple[str] = (
    SequentialFilter.INTERNAL_PROPAGATION_LABEL,
    SequentialFilter.INTERNAL_OBSERVATION_LABEL,
)
"""``tuple[str]``: Valid entries for :py:attr:`SequentialFilter.source` of filter measurement updates & estimates."""


_MANEUVER_DETECTION_MAP: Dict[str, ManeuverDetection] = {
    StandardNis.LABEL: StandardNis,
    SlidingNis.LABEL: SlidingNis,
    FadingMemoryNis.LABEL: FadingMemoryNis,
}


VALID_MANEUVER_DETECTION_LABELS: Tuple[str] = tuple(_MANEUVER_DETECTION_MAP.keys())
"""``tuple[str]``: Valid entries for :py:data:`'maneuver_detection'` key in filter configuration."""


_ADAPTIVE_ESTIMATION_MAP: Dict[str, AdaptiveFilter] = {
    GeneralizedPseudoBayesian1.LABELS: GeneralizedPseudoBayesian1,
    StaticMultipleModel.LABELS: StaticMultipleModel,
}


VALID_ADAPTIVE_ESTIMATION_LABELS: Tuple[str] = tuple(_ADAPTIVE_ESTIMATION_MAP.keys())
"""``tuple[str]``: Valid entries for :py:data:`'adaptive_estimation'` key in filter configuration."""


_FILTER_MAP: Dict[str, SequentialFilter] = {
    **{label: UnscentedKalmanFilter for label in UnscentedKalmanFilter.LABELS},
}


VALID_FILTER_LABELS: Tuple[str] = tuple(_FILTER_MAP.keys())
"""``tuple[str]``: Valid entries for the :py:data:`'name'` key in filter configuration."""


def sequentialFilterFactory(
    config: SequentialFilterConfig,
    tgt_id: int,
    time: ScenarioTime,
    est_x: ndarray,
    est_p: ndarray,
    dynamics: Dynamics,
    q_matrix: ndarray,
) -> SequentialFilter:
    """Build a :class:`.SequentialFilter` object for target state estimation.

    Args:
        config (:class:`.SequentialFilterConfig`): describes the filter to be built
        tgt_id (``int``): unique ID of the associated target agent
        time (:class:`.ScenarioTime`): initial time of scenario
        est_x (``ndarray``): 6x1, initial state estimate
        est_p (``ndarray``): 6x6, initial error covariance matrix
        dynamics (:class:`.Dynamics`): dynamics object to propagate estimate
        q_matrix (``ndarray``): process noise covariance matrix

    Returns:
        :class:`.SequentialFilter`: constructed filter object
    """
    # Create the base estimation filter for nominal operation
    if config.name in VALID_FILTER_LABELS:
        nominal_filter = _FILTER_MAP[config.name](
            tgt_id,
            time,
            est_x,
            est_p,
            dynamics,
            q_matrix,
            maneuverDetectionFactory(config.maneuver_detection),
            config.adaptive_estimation,
            **config.parameters,
        )
    else:
        raise ValueError(f"Invalid filter type: {config.name}")

    return nominal_filter


def maneuverDetectionFactory(config: ManeuverDetectionConfig) -> ManeuverDetection:
    """Build a maneuver detection class for use in filtering.

    Args:
        config (:class:`.ManeuverDetectionConfig`): the configuration used to generate the maneuver detection test
            technique.

    Returns:
        :class:`.ManeuverDetection`: maneuver detection class.

    Raises:
        ValueError: raised if `config.name` is invalid.
    """
    if not config.name:
        return None

    if config.name in VALID_MANEUVER_DETECTION_LABELS:
        nis_class = _MANEUVER_DETECTION_MAP[config.name]
    else:
        raise ValueError(f"Invalid maneuver detection type: {config.name}")

    return nis_class(config.threshold, **config.parameters)


def adaptiveEstimationFactory(
    config: AdaptiveEstimationConfig, nominal_filter: SequentialFilter, time_step: ScenarioTime
) -> AdaptiveFilter:
    """Build an adaptive estimation class for use in filtering.

    Args:
        config (:class:`.AdaptiveEstimationConfig`): the configuration used to generate the
            adaptive estimator.

    Returns:
        :class:`.AdaptiveFilter`: adaptive estimation class.

    Raises:
        ValueError: raised if `config.name` is invalid.
    """
    # Create the base estimation filter for nominal operation
    if config.name in VALID_ADAPTIVE_ESTIMATION_LABELS:
        adaptive_filter = _ADAPTIVE_ESTIMATION_MAP[config.name].fromConfig(
            config, nominal_filter, time_step
        )
    else:
        raise ValueError(f"Invalid adaptive estimation type: {config.name}")

    return adaptive_filter
