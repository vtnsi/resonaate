"""Contains all classes and functions related to estimation theory.

This includes Kalman filter classes, statistical tests, and debugging utility functions.
"""
from __future__ import annotations

# Standard Library Imports
from typing import TYPE_CHECKING

# Local Imports
from ..common.labels import AdaptiveEstimationLabel, ManeuverDetectionLabel, SequentialFilterLabel
from .adaptive.adaptive_filter import AdaptiveFilter
from .adaptive.gpb1 import GeneralizedPseudoBayesian1
from .adaptive.initialization import VALID_LAMBERT_IOD_LABELS
from .adaptive.smm import StaticMultipleModel
from .initial_orbit_determination import LambertIOD
from .maneuver_detection import FadingMemoryNis, ManeuverDetection, SlidingNis, StandardNis
from .sequential.sequential_filter import SequentialFilter
from .sequential.unscented_kalman_filter import UnscentedKalmanFilter

# Type Checking Imports
if TYPE_CHECKING:
    # Third Party Imports
    from numpy import ndarray

    # Local Imports
    from ..dynamics.dynamics_base import Dynamics
    from ..physics.time.stardate import JulianDate, ScenarioTime
    from ..scenario.config.estimation_config import (
        AdaptiveEstimationConfig,
        InitialOrbitDeterminationConfig,
        ManeuverDetectionConfig,
        SequentialFilterConfig,
    )
    from .initial_orbit_determination import InitialOrbitDetermination


VALID_ESTIMATE_SOURCES: tuple[str] = (
    SequentialFilter.INTERNAL_PROPAGATION_SOURCE,
    SequentialFilter.INTERNAL_OBSERVATION_SOURCE,
)
"""``tuple[str]``: Valid entries for :py:attr:`SequentialFilter.source` of filter measurement updates & estimates."""


_MANEUVER_DETECTION_MAP: dict[str, ManeuverDetection] = {
    ManeuverDetectionLabel.STANDARD_NIS: StandardNis,
    ManeuverDetectionLabel.SLIDING_NIS: SlidingNis,
    ManeuverDetectionLabel.FADING_MEMORY_NIS: FadingMemoryNis,
}


VALID_MANEUVER_DETECTION_LABELS: tuple[str] = tuple(_MANEUVER_DETECTION_MAP.keys())
"""``tuple[str]``: Valid entries for :py:data:`'maneuver_detection'` key in filter configuration."""


_ADAPTIVE_ESTIMATION_MAP: dict[str, AdaptiveFilter] = {
    AdaptiveEstimationLabel.GPB1: GeneralizedPseudoBayesian1,
    AdaptiveEstimationLabel.SMM: StaticMultipleModel,
}


VALID_ADAPTIVE_ESTIMATION_LABELS: tuple[str] = tuple(_ADAPTIVE_ESTIMATION_MAP.keys())
"""``tuple[str]``: Valid entries for :py:data:`'adaptive_estimation'` key in filter configuration."""


_FILTER_MAP: dict[str, SequentialFilter] = {
    SequentialFilterLabel.UKF: UnscentedKalmanFilter,
    SequentialFilterLabel.UNSCENTED_KALMAN_FILTER: UnscentedKalmanFilter,
}


VALID_FILTER_LABELS: tuple[str] = tuple(_FILTER_MAP.keys())
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
            config.initial_orbit_determination,
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
    if not config:
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
        nominal_filter (:class:`.SequentialFilter`): the current estimate's nominal filter
        time_step (:class:`.ScenarioTime`): the scenario level time step

    Returns:
        :class:`.AdaptiveFilter`: adaptive estimation class.

    Raises:
        ValueError: raised if `config.name` is invalid.
    """
    # Create the base estimation filter for nominal operation
    if config is None:
        raise ValueError("Adaptive estimation turned on by sequential filter, but no config given")
    if config.name in VALID_ADAPTIVE_ESTIMATION_LABELS:
        adaptive_filter = _ADAPTIVE_ESTIMATION_MAP[config.name].fromConfig(
            config, nominal_filter, time_step
        )
    else:
        raise ValueError(f"Invalid adaptive estimation type: {config.name}")

    return adaptive_filter


def initialOrbitDeterminationFactory(
    config: InitialOrbitDeterminationConfig, sat_num: int, julian_date_start: JulianDate
) -> InitialOrbitDetermination:
    """Build an initial orbit determination class for use in filtering.

    Args:
        config (:class:`.InitialOrbitDeterminationConfig`): the configuration used to generate the
            adaptive estimator.
        sat_num (``int``): satcat ID of Estimate
        julian_date_start (:class:`.JulianDate`): Scenario starting JulianDate

    Returns:
        :class:`.InitialOrbitDetermination`: adaptive estimation class.

    Raises:
        ValueError: raised if `config.name` is invalid.
    """
    if not config:
        return None

    if config.name in VALID_LAMBERT_IOD_LABELS:
        return LambertIOD.fromConfig(config, sat_num, julian_date_start)

    raise ValueError(f"Invalid Initial Orbit Determination type: {config.name}")
