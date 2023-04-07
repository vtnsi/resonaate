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

    background: bool = True
    """``bool``: whether or not to do field of view on background rso calculations."""

    realtime_observation: bool = True
    """``bool``: whether to generate observations during the simulation."""
