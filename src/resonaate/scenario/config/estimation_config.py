"""Submodule defining the 'estimation' configuration section."""

from __future__ import annotations

# Standard Library Imports
from typing import Annotated, Literal, Optional, Union
from warnings import warn

# Third Party Imports
from pydantic import BaseModel, ConfigDict, Field, model_validator
from typing_extensions import Self

# Local Imports
from ...common.labels import (
    AdaptiveEstimationLabel,
    DynamicsLabel,
    InitialOrbitDeterminationLabel,
    ManeuverDetectionLabel,
    SequentialFilterLabel,
    StackingLabel,
)

# ruff: noqa: UP007

DEFAULT_MANEUVER_DETECTION_THRESHOLD: float = 0.05
DEFAULT_PRUNE_PERCENTAGE: float = 0.997
DEFAULT_PRUNE_THRESHOLD: float = 1e-20
DEFAULT_OBSERVATION_WINDOW: int = 3
DEFAULT_MODEL_TIME_INTERVAL: int = 60
DEFAULT_IOD_OBSERVATION_SPACING: int = 60


class EstimationConfig(BaseModel):
    """Configuration section defining several estimation-based options."""

    sequential_filter: SequentialFilterConfig
    """:class:`.SequentialFilterConfig`: sequential technique as nested item."""

    adaptive_filter: Union[AdaptiveEstimationConfig, None] = None
    """:class:`.AdaptiveEstimationConfig`: adaptive estimation technique as nested item."""

    initial_orbit_determination: Union[InitialOrbitDeterminationConfig, None] = None
    """:class:`.InitialOrbitDeterminationConfig`: initial orbit determination technique as nested item."""

    @model_validator(mode="after")
    def clarifyFlags(self) -> Self:
        """Make sure flags are consistent with populated configurations."""
        if (
            self.sequential_filter.adaptive_estimation
            and self.sequential_filter.initial_orbit_determination
        ):
            raise ValueError("IOD & MMAE cannot both be used at the same time.")

        if self.sequential_filter.adaptive_estimation:
            if self.adaptive_filter is None:
                raise ValueError(
                    "Adaptive estimation flag set but no configuration specified.",
                )
        elif self.adaptive_filter is not None:
            warn(
                "Adaptive estimation flag is OFF, specified configuration will be IGNORED!",
                stacklevel=2,
            )

        if self.sequential_filter.initial_orbit_determination:
            if self.initial_orbit_determination is None:
                raise ValueError("IOD flag set but no configuration specified.")
        elif self.initial_orbit_determination is not None:
            warn("IOD flag is OFF, specified configuration will be IGNORED!", stacklevel=2)

        return self


class SequentialFilterConfigBase(BaseModel):
    """Configuration section defining several sequential filter-based options."""

    dynamics_model: DynamicsLabel = DynamicsLabel.SPECIAL_PERTURBATIONS
    """``str``: name of the dynamics to use in the filter."""

    maneuver_detection: Union[ManeuverDetectionConfig, None] = None
    """:class:`.ManeuverDetectionConfig`: maneuver detection technique."""

    adaptive_estimation: bool = False
    """``bool``: Check if sequential filter should turn on adaptive estimation."""

    initial_orbit_determination: bool = False
    """``bool``: Check if sequential filter should turn on initial orbit determination."""

    save_filter_steps: bool = False
    """``bool``: Check if you would like to enable saving filter steps to the database. Defaults to False."""


class UKFConfigBase(SequentialFilterConfigBase):
    """Configuration section defining parameters for an Unscented Kalman Filter."""

    resample: bool = False
    """``bool``: Flag indicating whether sigma points should be resampled.

    See Also:
        :class:`.resonaate.estimation.UnscentedKalmanFilter` constructor argument ``resample``.
    """

    alpha: float = Field(default=0.001, lt=1.0, gt=0.0)
    """``float``: Sigma point spread.

    See Also:
        :class:`.resonaate.estimation.UnscentedKalmanFilter` constructor argument ``alpha``.
    """

    beta: float = 2.0
    """``float``: Gaussian pdf parameter.

    See Also:
        :class:`.resonaate.estimation.UnscentedKalmanFilter` constructor argument ``beta``.
    """

    kappa: Optional[float] = None
    """``float``: Scaling parameter defining knowledge of higher order moments.

    See Also:
        :class:`.resonaate.estimation.UnscentedKalmanFilter` constructor argument ``kappa``.
    """


class UKFConfig(UKFConfigBase):
    """Configuration section defining parameters for an Unscented Kalman Filter."""

    name: Literal[SequentialFilterLabel.UKF] = SequentialFilterLabel.UKF
    """``str``: name of the sequential filter algorithm to use."""


class UnscentedKalmanFilterConfig(UKFConfigBase):
    """Configuration section defining parameters for an Unscented Kalman Filter."""

    name: Literal[SequentialFilterLabel.UNSCENTED_KALMAN_FILTER] = (
        SequentialFilterLabel.UNSCENTED_KALMAN_FILTER
    )
    """``str``: name of the sequential filter algorithm to use."""


class GPFConfigBase(SequentialFilterConfigBase):
    """Configuration section defining parameters for an Unscented Kalman Filter."""

    population_size: int = 100
    """``int``: Determines the population size to evolve over time

    See Also:
        :class:`.resonaate.estimation.GeneticParticleFilter` constructor argument ``population``.
    """

    num_purge: int = 10
    """``int``: The number of bottom performers to remove

    See Also:
        :class:`.resonaate.estimation.GeneticParticleFilter` constructor argument ``num_purge``
    """

    num_keep: int = 10
    """``int``: The number of top performers to keep

    See Also:
        :class:`.resonaate.estimation.GeneticParticleFilter` constructor argument ``num_keep``
    """

    num_mutate: int = 50
    """``int``: The number of population members to mutate, excluding the top performers

    See Also:
        :class:`.resonaate.estimation.GeneticParticleFilter` constructor argument ``num_mutate``
    """

    mutation_strength: Union[list[float], None] = None
    """``list[float]``: The strength of mutations for each state vector entry

    See Also:
        :class:`.resonaate.estimation.GeneticParticleFilter` constructor argument ``mutation_strength``
    """


class GPFConfig(GPFConfigBase):
    """Configuration section defining parameters for an Unscented Kalman Filter."""

    name: Literal[SequentialFilterLabel.GPF] = SequentialFilterLabel.GPF
    """``str``: name of the sequential filter algorithm to use."""


class GeneticParticleFilterConfig(GPFConfigBase):
    """Configuration section defining parameters for an Unscented Kalman Filter."""

    name: Literal[SequentialFilterLabel.GENETIC_PARTICLE_FILTER] = (
        SequentialFilterLabel.GENETIC_PARTICLE_FILTER
    )
    """``str``: name of the sequential filter algorithm to use."""


SequentialFilterConfig = Annotated[
    Union[UKFConfig, UnscentedKalmanFilterConfig, GPFConfig, GeneticParticleFilterConfig],
    Field(..., discriminator="name"),
]
"""Annotated[Union]: Discriminated union defining valid sequential filter configurations."""


class ManeuverDetectionConfigBase(BaseModel):
    """Configuration section defining maneuver detection options."""

    threshold: float = Field(DEFAULT_MANEUVER_DETECTION_THRESHOLD, gt=0.0, lt=1.0)
    R"""``float``: lower tail value for :math:`\chi^2` maneuver detection threshold."""


class StandardNISConfig(ManeuverDetectionConfigBase):
    """Configuration section defining configuration options for standard NIS maneuver detection."""

    name: Literal[ManeuverDetectionLabel.STANDARD_NIS] = ManeuverDetectionLabel.STANDARD_NIS
    """``str``: maneuver detection technique to use."""


class SlidingNISConfig(ManeuverDetectionConfigBase):
    """Configuration section defining configuration options for sliding NIS maneuver detection."""

    name: Literal[ManeuverDetectionLabel.SLIDING_NIS] = ManeuverDetectionLabel.SLIDING_NIS
    """``str``: maneuver detection technique to use."""

    window_size: int = 4
    """``int``: length of the sliding window used to "average" NIS over multiple timesteps."""


class FadingMemoryNISConfig(ManeuverDetectionConfigBase):
    """Configuration section defining configuration options for fading-memory NIS maneuver detection."""

    name: Literal[ManeuverDetectionLabel.FADING_MEMORY_NIS] = (
        ManeuverDetectionLabel.FADING_MEMORY_NIS
    )
    """``str``: maneuver detection technique to use."""

    delta: float = Field(default=0.8, gt=0.0, lt=1.0)
    """``float``: scale by which previous NIS values are weighted"""


ManeuverDetectionConfig = Annotated[
    Union[StandardNISConfig, SlidingNISConfig, FadingMemoryNISConfig],
    Field(..., discriminator="name"),
]
"""Annotated[Union]: Discriminated union defining valid maneuver detection configurations."""


class AdaptiveEstimationConfigBase(BaseModel):
    """Configuration section defining adaptive estimation options."""

    model_config = ConfigDict(
        protected_namespaces=(),
    )
    """ConfigDict: Configuration management for ``pydantic.BaseModel`` class.

    The ``protected_namespaces`` attribute is set to an empty tuple to avoid a warning being thrown
    about :attr:`.model_interval`.
    """

    orbit_determination: InitialOrbitDeterminationLabel = (
        InitialOrbitDeterminationLabel.LAMBERT_UNIVERSAL
    )
    """``str``: orbit determination technique used to initialize the adaptive filter."""

    stacking_method: StackingLabel = StackingLabel.ECI_STACKING
    """``str``: state vector coordinate system stacking technique."""

    model_interval: int = Field(DEFAULT_MODEL_TIME_INTERVAL, gt=0)
    """``int``: time step between MMAE models in seconds."""

    observation_window: int = Field(DEFAULT_OBSERVATION_WINDOW, gt=0)
    """``int``: number of previous observations to go back to to start adaptive estimation."""

    prune_threshold: float = Field(DEFAULT_PRUNE_THRESHOLD, gt=0.0, lt=1.0)
    """``float``: likelihood that a model has to be less than to be pruned off."""

    prune_percentage: float = Field(DEFAULT_PRUNE_PERCENTAGE, gt=0.0, lt=1.0)
    """``float``: percent likelihood a model has to meet to trigger MMAE convergence."""


class GPB1AdaptiveEstimationConfig(AdaptiveEstimationConfigBase):
    """Configuration section defining Generalized Pseudo-Bayesian 1 adaptive estimation options."""

    name: Literal[AdaptiveEstimationLabel.GPB1] = AdaptiveEstimationLabel.GPB1
    """``str``: Name of adaptive estimation method to use."""

    mix_ratio: float = 1.5
    """``float``: ratio of diagonal to off-diagonals in transition probability matrix"""


class SMMAdaptiveEstimationConfig(AdaptiveEstimationConfigBase):
    """Configuration section defining static multiple model adaptive estimation options."""

    name: Literal[AdaptiveEstimationLabel.SMM] = AdaptiveEstimationLabel.SMM
    """``str``: Name of adaptive estimation method to use."""


AdaptiveEstimationConfig = Annotated[
    Union[GPB1AdaptiveEstimationConfig, SMMAdaptiveEstimationConfig],
    Field(..., discriminator="name"),
]
"""Annotated[Union]: Discriminated union defining valid adaptive estimation configurations."""


class InitialOrbitDeterminationConfig(BaseModel):
    """Configuration section defining initial orbit determination options."""

    name: InitialOrbitDeterminationLabel = InitialOrbitDeterminationLabel.LAMBERT_UNIVERSAL
    """``str``: Name of initial orbit determination method to use."""

    minimum_observation_spacing: int = Field(DEFAULT_IOD_OBSERVATION_SPACING, gt=0)
    """``int``: Minimum amount of seconds allowed between each observation used for IOD."""
