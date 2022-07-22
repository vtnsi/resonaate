"""Submodule defining the 'decision' configuration section."""
from __future__ import annotations

# Standard Library Imports
from dataclasses import dataclass, field
from typing import ClassVar

# Local Imports
from ...tasking.decisions import VALID_DECISIONS
from .base import ConfigObject, ConfigValueError


@dataclass
class DecisionConfig(ConfigObject):
    """Configuration section defining several decision-based options."""

    CONFIG_LABEL: ClassVar[str] = "decision"
    """``str``: Key where settings are stored in the configuration dictionary."""

    name: str
    """``str``: Name of this decision function."""

    parameters: dict = field(default_factory=dict)
    """``dict``: Parameters for the decision function."""

    def __post_init__(self):
        """Runs after the object is initialized."""
        if self.name not in VALID_DECISIONS:
            raise ConfigValueError("name", self.name, VALID_DECISIONS)
