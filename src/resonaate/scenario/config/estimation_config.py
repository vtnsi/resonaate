"""Submodule defining the 'estimation' configuration section."""

from __future__ import annotations

# Standard Library Imports
from dataclasses import dataclass, field
from typing import ClassVar

# Local Imports
from ...common.labels import DynamicsLabel, InitialOrbitDeterminationLabel, StackingLabel
from ...estimation import (
    VALID_ADAPTIVE_ESTIMATION_LABELS,
    VALID_FILTER_LABELS,
    VALID_MANEUVER_DETECTION_LABELS,
)
from ...estimation.adaptive.initialization import VALID_LAMBERT_IOD_LABELS
from ...estimation.adaptive.mmae_stacking_utils import VALID_STACKING_LABELS
from .base import ConfigObject, ConfigValueError

VALID_FILTER_DYNAMICS: tuple[str] = (
    DynamicsLabel.TWO_BODY,
    DynamicsLabel.SPECIAL_PERTURBATIONS,
)
DEFAULT_MANEUVER_DETECTION_THRESHOLD: float = 0.05
DEFAULT_PRUNE_PERCENTAGE: float = 0.997
DEFAULT_PRUNE_THRESHOLD: float = 1e-20
DEFAULT_OBSERVATION_WINDOW: int = 3
DEFAULT_MODEL_TIME_INTERVAL: int = 60
DEFAULT_IOD_OBSERVATION_SPACING: int = 60


@dataclass
class EstimationConfig(ConfigObject):
    """Configuration section defining several estimation-based options."""

    CONFIG_LABEL: ClassVar[str] = "estimation"
    """``str``: Key where settings are stored in the configuration dictionary."""

    sequential_filter: SequentialFilterConfig | dict
    """:class:`.SequentialFilterConfig`: sequential technique as nested item."""

    adaptive_filter: AdaptiveEstimationConfig | dict | None = None
    """:class:`.AdaptiveEstimationConfig`: adaptive estimation technique as nested item."""

    initial_orbit_determination: InitialOrbitDeterminationConfig | dict | None = None
    """:class:`.InitialOrbitDeterminationConfig`: initial orbit determination technique as nested item."""

    def __post_init__(self):
        """Runs after the object is initialized."""
        if isinstance(self.sequential_filter, dict):
            self.sequential_filter = SequentialFilterConfig(**self.sequential_filter)

        if isinstance(self.adaptive_filter, dict):
            self.adaptive_filter = AdaptiveEstimationConfig(**self.adaptive_filter)

        if isinstance(self.initial_orbit_determination, dict):
            self.initial_orbit_determination = InitialOrbitDeterminationConfig(
                **self.initial_orbit_determination,
            )


@dataclass
class SequentialFilterConfig(ConfigObject):
    """Configuration section defining several sequential filter-based options."""

    CONFIG_LABEL: ClassVar[str] = "sequential_filter"
    """``str``: Key where settings are stored in the configuration dictionary."""

    name: str
    """``str``: name of the sequential filter algorithm to use."""

    dynamics_model: str = DynamicsLabel.SPECIAL_PERTURBATIONS
    """``str``: name of the dynamics to use in the filter."""

    maneuver_detection: ManeuverDetectionConfig | dict | None = None
    """:class:`.ManeuverDetectionConfig`: maneuver detection technique."""

    adaptive_estimation: bool = False
    """``bool``: Check if sequential filter should turn on adaptive estimation."""

    initial_orbit_determination: bool = False
    """``bool``: Check if sequential filter should turn on initial orbit determination."""

    parameters: dict = field(default_factory=dict)
    """``dict``: extra parameters for the filter algorithm."""

    def __post_init__(self):
        """Runs after the object is initialized."""
        if self.name not in VALID_FILTER_LABELS:
            raise ConfigValueError("name", self.name, VALID_FILTER_LABELS)

        if self.dynamics_model not in VALID_FILTER_DYNAMICS:
            raise ConfigValueError("dynamics_model", self.dynamics_model, VALID_FILTER_DYNAMICS)

        if isinstance(self.maneuver_detection, dict):
            self.maneuver_detection = ManeuverDetectionConfig(**self.maneuver_detection)


@dataclass
class ManeuverDetectionConfig(ConfigObject):
    """Configuration section defining maneuver detection options."""

    CONFIG_LABEL: ClassVar[str] = "maneuver_detection"
    """``str``: Key where settings are stored in the configuration dictionary."""

    name: str
    """``str``: maneuver detection technique to use."""

    threshold: float = DEFAULT_MANEUVER_DETECTION_THRESHOLD
    R"""``float``: lower tail value for :math:`\chi^2` maneuver detection threshold."""

    parameters: dict = field(default_factory=dict)
    """``dict``: extra parameters for the maneuver detection technique."""

    def __post_init__(self):
        """Runs after the object is initialized."""
        if self.name not in VALID_MANEUVER_DETECTION_LABELS:
            raise ConfigValueError("name", self.name, VALID_MANEUVER_DETECTION_LABELS)

        if self.threshold <= 0.0 or self.threshold >= 1.0:
            raise ConfigValueError("threshold", self.threshold, "between 0 and 1")


@dataclass
class AdaptiveEstimationConfig(ConfigObject):
    """Configuration section defining adaptive estimation options."""

    CONFIG_LABEL: ClassVar[str] = "adaptive_filter"
    """``str``: Key where settings are stored in the configuration dictionary."""

    name: str
    """``str``: Name of adaptive estimation method to use."""

    orbit_determination: str = InitialOrbitDeterminationLabel.LAMBERT_UNIVERSAL
    """``str``: orbit determination technique used to initialize the adaptive filter."""

    stacking_method: str = StackingLabel.ECI_STACKING
    """``str``: state vector coordinate system stacking technique."""

    model_interval: int = DEFAULT_MODEL_TIME_INTERVAL
    """``int``: time step between MMAE models in seconds."""

    observation_window: int = DEFAULT_OBSERVATION_WINDOW
    """``int``: number of previous observations to go back to to start adaptive estimation."""

    prune_threshold: float = DEFAULT_PRUNE_THRESHOLD
    """``float``: likelihood that a model has to be less than to be pruned off."""

    prune_percentage: float = DEFAULT_PRUNE_PERCENTAGE
    """``float``: percent likelihood a model has to meet to trigger MMAE convergence."""

    parameters: dict = field(default_factory=dict)
    """``dict``: extra parameters for the adaptive estimation technique."""

    def __post_init__(self):
        """Runs after the object is initialized."""
        if self.name not in VALID_ADAPTIVE_ESTIMATION_LABELS:
            raise ConfigValueError("name", self.name, VALID_ADAPTIVE_ESTIMATION_LABELS)

        if self.orbit_determination not in VALID_LAMBERT_IOD_LABELS:
            raise ConfigValueError(
                "orbit_determination",
                self.orbit_determination,
                VALID_LAMBERT_IOD_LABELS,
            )

        if self.stacking_method not in VALID_STACKING_LABELS:
            raise ConfigValueError("stacking_method", self.stacking_method, VALID_STACKING_LABELS)

        if self.model_interval <= 0:
            raise ConfigValueError("model_interval", self.model_interval, "must be positive")

        if self.observation_window <= 0:
            raise ConfigValueError(
                "observation_window",
                self.observation_window,
                "must be positive",
            )

        if self.prune_threshold <= 0.0 or self.prune_threshold >= 1.0:
            raise ConfigValueError(
                "prune_threshold",
                self.prune_threshold,
                "must be between 0 and 1",
            )

        if self.prune_percentage <= 0.0 or self.prune_percentage >= 1.0:
            raise ConfigValueError(
                "prune_percentage",
                self.prune_percentage,
                "must be between 0 and 1",
            )


@dataclass
class InitialOrbitDeterminationConfig(ConfigObject):
    """Configuration section defining initial orbit determination options."""

    CONFIG_LABEL: ClassVar[str] = "initial_orbit_determination"
    """``str``: Key where settings are stored in the configuration dictionary read from file."""

    name: str = InitialOrbitDeterminationLabel.LAMBERT_UNIVERSAL
    """``str``: Name of initial orbit determination method to use."""

    minimum_observation_spacing: int = DEFAULT_IOD_OBSERVATION_SPACING
    """``int``: Minimum amount of seconds allowed between each observation used for IOD."""

    def __post_init__(self):
        """Runs after the object is initialized."""
        if self.name not in VALID_LAMBERT_IOD_LABELS:
            raise ConfigValueError(
                "name",
                self.name,
                VALID_LAMBERT_IOD_LABELS,
            )

        if self.minimum_observation_spacing <= 0:
            raise ConfigValueError(
                "minimum_observation_spacing",
                self.minimum_observation_spacing,
                "must be positive",
            )
