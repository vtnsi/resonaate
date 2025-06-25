"""Submodule defining the 'time' configuration section."""

# ruff: noqa: TCH003

from __future__ import annotations

# Standard Library Imports
from datetime import datetime

# Third Party Imports
from pydantic import BaseModel, Field, field_validator, model_validator
from typing_extensions import Self

DEFAULT_TIME_STEP: int = 60
"""``int``: Default time step in seconds."""


class TimeConfig(BaseModel):
    """Configuration section defining several time-based options."""

    start_timestamp: datetime
    """``str | datetime``: epoch at which the simulation starts."""

    stop_timestamp: datetime
    """``str | datetime``: epoch at which the scenario stops."""

    physics_step_sec: int = Field(default=DEFAULT_TIME_STEP, gt=1)
    """``int``: time step used for propagation. Defaults to 60 seconds."""

    output_step_sec: int = Field(default=DEFAULT_TIME_STEP, gt=1)
    """``int``: time step used for outputting data. Defaults to 60 seconds."""

    @field_validator("start_timestamp", "stop_timestamp")
    @classmethod
    def ignore_tzinfo(cls, val: datetime):
        """Remove any timezone info from datetime fields."""
        if val.tzinfo:
            val = val.replace(tzinfo=None)
        return val

    @model_validator(mode="after")
    def stop_after_start(self) -> Self:
        """Validate that :attr:`.start_timestamp` is before :attr:`.end_timestamp`."""
        if self.start_timestamp >= self.stop_timestamp:
            raise ValueError("Stop timestamp must be after start timestamp")
        return self
