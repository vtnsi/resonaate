"""Submodule defining the 'perturbations' configuration section."""

from __future__ import annotations

# Standard Library Imports
from enum import Enum

# Third Party Imports
from pydantic import BaseModel, Field


class ThirdBody(str, Enum):
    """Enumeration of valid third bodies."""

    MOON = "moon"
    SUN = "sun"
    JUPITER = "jupiter"
    SATURN = "saturn"
    VENUS = "venus"


class PerturbationsConfig(BaseModel):
    """Configuration section defining several perturbations options."""

    third_bodies: list[ThirdBody] = Field(default_factory=list)
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
