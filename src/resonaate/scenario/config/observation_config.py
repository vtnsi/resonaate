"""Submodule defining the 'observation' configuration section."""
from __future__ import annotations

# Standard Library Imports
from dataclasses import dataclass
from typing import ClassVar

# Local Imports
from .base import ConfigObject


@dataclass
class ObservationConfig(ConfigObject):
    """Configuration section defining several observation-based options."""

    CONFIG_LABEL: ClassVar[str] = "observation"
    """``str``: Key where settings are stored in the configuration dictionary."""

    field_of_view: bool = True
    """``bool``: whether or not to do field of view calculations.

    Note:
        This setting turns background (serendipitous) observations on for all sensors. This will
        also force each sensor to have a FOV config.
    """
