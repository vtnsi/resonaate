"""Submodule defining the 'estimation' configuration section."""

from __future__ import annotations

# Standard Library Imports
from typing import Union

# Third Party Imports
from pydantic import BaseModel, ConfigDict, Field

# Local Imports
from ...common.labels import (
    AdaptiveEstimationLabel,
    DynamicsLabel,
    InitialOrbitDeterminationLabel,
    ManeuverDetectionLabel,
    SequentialFilterLabel,
    StackingLabel,
)

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


class SequentialFilterConfig(BaseModel):
    """Configuration section defining several sequential filter-based options."""

    name: SequentialFilterLabel
    """``str``: name of the sequential filter algorithm to use."""

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

    parameters: dict = Field(default_factory=dict)
    """``dict``: extra parameters for the filter algorithm."""


class ManeuverDetectionConfig(BaseModel):
    """Configuration section defining maneuver detection options."""

    name: ManeuverDetectionLabel
    """``str``: maneuver detection technique to use."""

    threshold: float = Field(DEFAULT_MANEUVER_DETECTION_THRESHOLD, gt=0.0, lt=1.0)
    R"""``float``: lower tail value for :math:`\chi^2` maneuver detection threshold."""

    parameters: dict = Field(default_factory=dict)
    """``dict``: extra parameters for the maneuver detection technique."""


class AdaptiveEstimationConfig(BaseModel):
    """Configuration section defining adaptive estimation options."""

    model_config = ConfigDict(
        protected_namespaces=()
    )
    """ConfigDict: Configuration management for ``pydantic.BaseModel`` class.

    The ``protected_namespaces`` attribute is set to an empty tuple to avoid a warning being thrown
    about :attr:`.model_interval`.
    """

    name: AdaptiveEstimationLabel
    """``str``: Name of adaptive estimation method to use."""

    orbit_determination: InitialOrbitDeterminationLabel = InitialOrbitDeterminationLabel.LAMBERT_UNIVERSAL
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

    parameters: dict = Field(default_factory=dict)
    """``dict``: extra parameters for the adaptive estimation technique."""


class InitialOrbitDeterminationConfig(BaseModel):
    """Configuration section defining initial orbit determination options."""

    name: InitialOrbitDeterminationLabel = InitialOrbitDeterminationLabel.LAMBERT_UNIVERSAL
    """``str``: Name of initial orbit determination method to use."""

    minimum_observation_spacing: int = Field(DEFAULT_IOD_OBSERVATION_SPACING, gt=0)
    """``int``: Minimum amount of seconds allowed between each observation used for IOD."""
