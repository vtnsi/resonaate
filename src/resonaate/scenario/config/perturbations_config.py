"""Submodule defining the 'perturbations' configuration section."""

from __future__ import annotations

# Standard Library Imports
from dataclasses import dataclass, field
from typing import ClassVar

# Local Imports
from .base import ConfigObject, ConfigValueError

SUPPORTED_THIRD_BODIES: tuple[str] = (
    "moon",
    "sun",
    "jupiter",
    "saturn",
    "venus",
)
"""``tuple``: currently supported third-body perturbation configs."""


@dataclass
class PerturbationsConfig(ConfigObject):
    """Configuration section defining several perturbations options."""

    CONFIG_LABEL: ClassVar[str] = "perturbations"
    """``str``: Key where settings are stored in the configuration dictionary."""

    third_bodies: list[str] = field(default_factory=list)
    """``list[str]``: names of third body objects to use in special perturbations dynamics.

    Currently the following third bodies are supported:
         * `"sun"`
         * `"moon"`
         * `"jupiter"`
         * `"saturn"`
         * `"venus"`
    """

    solar_radiation_pressure: bool = False
    """``bool``: whether to account for solar radiation pressure in special perturbations dynamics."""

    general_relativity: bool = False
    """``bool``: whether to account for general relativity in special perturbations dynamics."""

    def __post_init__(self):
        """Runs after the object is initialized."""
        for third_body in self.third_bodies:
            if third_body not in SUPPORTED_THIRD_BODIES:
                raise ConfigValueError("third_bodies", third_body, SUPPORTED_THIRD_BODIES)
