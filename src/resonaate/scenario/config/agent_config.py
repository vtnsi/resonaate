"""Module that defines the objects stored in the 'targets' and 'sensors' configuration sections."""

# ruff: noqa: TCH001

from __future__ import annotations

# Third Party Imports
from pydantic import BaseModel, model_validator
from typing_extensions import Self

# Local Imports
from ...physics.orbits import ResidentStratification
from .platform_config import PlatformConfig
from .sensor_config import SensorConfig
from .state_config import StateConfig


class AgentConfig(BaseModel):
    R"""Configuration base class defining an agent."""

    id: int
    R"""``int``: unique ID of the agent."""

    name: str
    R"""``str``: name of the agent."""

    state: StateConfig
    R""":class:`.StateConfig`: defines the location/dynamics of this agent."""

    platform: PlatformConfig
    R""":class:`.PlatformConfig`: defines the behavior/dynamics of this agent."""

    @model_validator(mode="after")
    def validate_strat(self) -> Self:
        """Make sure platform and resident stratification match and then set any associated default values."""
        altitude = self.state.getAltitude()
        if not self.platform.isAltitudeValid(altitude):
            err = f"Invalid altitude of {altitude} km specified for platform {self.platform.type}"
            raise ValueError(err)
        strat = ResidentStratification.getStratification(altitude)
        self.platform.setStratDefaults(strat)

        return self


class SensingAgentConfig(AgentConfig):
    R"""Configuration object for a :class:`.SensingAgent`."""

    sensor: SensorConfig
    R""":class:`.SensorConfig`: defines the sensor object of this sensing agent."""
