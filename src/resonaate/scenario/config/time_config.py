"""Submodule defining the 'time' configuration section."""
from __future__ import annotations

# Standard Library Imports
from dataclasses import dataclass
from datetime import datetime
from typing import ClassVar

# Local Imports
from .base import ConfigObject, ConfigValueError

DEFAULT_TIME_STEP: int = 60
"""``int``: Default time step in seconds."""

TIME_STAMP_FORMAT: str = "%Y-%m-%dT%H:%M:%S.%fZ"
"""``str``: Format string for time stamps."""


@dataclass
class TimeConfig(ConfigObject):
    """Configuration section defining several time-based options."""

    CONFIG_LABEL: ClassVar[str] = "time"
    """``str``: Key where settings are stored in the configuration dictionary."""

    start_timestamp: str | datetime
    """``str | datetime``: epoch at which the simulation starts."""

    stop_timestamp: str | datetime
    """``str | datetime``: epoch at which the scenario stops."""

    physics_step_sec: int = DEFAULT_TIME_STEP
    """``int``: time step used for propagation. Defaults to 60 seconds."""

    output_step_sec: int = DEFAULT_TIME_STEP
    """``int``: time step used for outputting data. Defaults to 60 seconds."""

    def __post_init__(self):
        """Runs after the object is initialized."""
        if isinstance(self.start_timestamp, str):
            self.start_timestamp = datetime.strptime(self.start_timestamp, TIME_STAMP_FORMAT)

        if isinstance(self.stop_timestamp, str):
            self.stop_timestamp = datetime.strptime(self.stop_timestamp, TIME_STAMP_FORMAT)

        if self.physics_step_sec <= 1:
            raise ConfigValueError("physics_step_sec", self.physics_step_sec, "> 1")

        if self.output_step_sec <= 1:
            raise ConfigValueError("output_step_sec", self.output_step_sec, "> 1")

        if self.start_timestamp >= self.stop_timestamp:
            raise ConfigValueError(
                "start_timestamp", self.start_timestamp, (f"before {self.stop_timestamp}",)
            )
