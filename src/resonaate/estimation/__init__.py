"""Contains all classes and functions related to estimation theory.

This includes Kalman filter classes, statistical tests, and debugging utility functions.
"""

from __future__ import annotations

# Standard Library Imports
from typing import TYPE_CHECKING

# Local Imports
from ..common.labels import (
    AdaptiveEstimationLabel,
    ManeuverDetectionLabel,
    ParticleFilterLabel,
    SequentialFilterLabel,
)
from .adaptive.adaptive_filter import AdaptiveFilter
from .adaptive.gpb1 import GeneralizedPseudoBayesian1
from .adaptive.smm import StaticMultipleModel
from .initial_orbit_determination import LambertIOD
from .maneuver_detection import FadingMemoryNis, ManeuverDetection, SlidingNis, StandardNis
from .particle.genetic_particle_filter import GeneticParticleFilter
from .particle.particle_filter import ParticleFilter
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
        ParticleFilterConfig,
        SequentialFilterConfig,
    )
    from .initial_orbit_determination import InitialOrbitDetermination


__all__ = [
    "AdaptiveFilter",
]

VALID_ESTIMATE_SOURCES: tuple[str] = (
    SequentialFilter.INTERNAL_PROPAGATION_SOURCE,
    SequentialFilter.INTERNAL_OBSERVATION_SOURCE,
    ParticleFilter.INTERNAL_PROPAGATION_SOURCE,
    ParticleFilter.INTERNAL_OBSERVATION_SOURCE,
)
"""``tuple[str]``: Valid entries for :py:attr:`SequentialFilter.source` of filter measurement updates & estimates."""


_MANEUVER_DETECTION_MAP: dict[str, type[ManeuverDetection]] = {
    ManeuverDetectionLabel.STANDARD_NIS: StandardNis,
    ManeuverDetectionLabel.SLIDING_NIS: SlidingNis,
    ManeuverDetectionLabel.FADING_MEMORY_NIS: FadingMemoryNis,
}


_ADAPTIVE_ESTIMATION_MAP: dict[str, type[AdaptiveFilter]] = {
    AdaptiveEstimationLabel.GPB1: GeneralizedPseudoBayesian1,
    AdaptiveEstimationLabel.SMM: StaticMultipleModel,
}


_SEQUENTIAL_FILTER_MAP: dict[str, type[SequentialFilter]] = {
    SequentialFilterLabel.UKF: UnscentedKalmanFilter,
    SequentialFilterLabel.UNSCENTED_KALMAN_FILTER: UnscentedKalmanFilter,
}

_PARTICLE_FILTER_MAP: dict[str, type[ParticleFilter]] = {
    ParticleFilterLabel.GPF: GeneticParticleFilter,
    ParticleFilterLabel.GENETIC_PARTICLE_FILTER: GeneticParticleFilter,
}


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
    maneuver_detection = maneuverDetectionFactory(config.maneuver_detection)
    return _SEQUENTIAL_FILTER_MAP[config.name].fromConfig(
        config,
        tgt_id,
        time,
        est_x,
        est_p,
        dynamics,
        q_matrix,
        maneuver_detection,
    )


def particleFilterFactory(
    config: ParticleFilterConfig,
    tgt_id: int,
    time: ScenarioTime,
    est_x: ndarray,
    est_p: ndarray,
    dynamics: Dynamics,
    q_matrix: ndarray,
) -> ParticleFilter:
    """Build a :class:`.ParticleFilter` object for target state estimation.

    Args:
        config (:class:`.ParticleFilterConfig`): describes the filter to be built
        tgt_id (``int``): unique ID of the associated target agent
        time (:class:`.ScenarioTime`): initial time of scenario
        est_x (``ndarray``): 6x1, initial state estimate
        est_p (``ndarray``): 6x6, initial error covariance matrix
        dynamics (:class:`.Dynamics`): dynamics object to propagate estimate
        q_matrix (``ndarray``): process noise covariance matrix

    Returns:
        :class:`.ParticleFilter`: constructed filter object
    """
    maneuver_detection = maneuverDetectionFactory(config.maneuver_detection)
    return _PARTICLE_FILTER_MAP[config.name].fromConfig(
        config,
        tgt_id,
        time,
        est_x,
        est_p,
        dynamics,
        q_matrix,
        maneuver_detection,
    )


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

    nis_class = _MANEUVER_DETECTION_MAP[config.name]
    return nis_class.fromConfig(config)


def adaptiveEstimationFactory(
    config: AdaptiveEstimationConfig,
    nominal_filter: SequentialFilter,
    time_step: ScenarioTime,
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

    return _ADAPTIVE_ESTIMATION_MAP[config.name].fromConfig(
        config,
        nominal_filter,
        time_step,
    )


def initialOrbitDeterminationFactory(
    config: InitialOrbitDeterminationConfig,
    sat_num: int,
    julian_date_start: JulianDate,
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

    return LambertIOD.fromConfig(config, sat_num, julian_date_start)
