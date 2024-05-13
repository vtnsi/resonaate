"""Module that defines the objects stored in the 'targets' and 'sensors' configuration sections."""

from __future__ import annotations

# Third Party Imports
from pydantic import BaseModel

# Local Imports
from .platform_config import PlatformConfig
from .sensor_config import SensorConfig
from .state_config import StateConfig

# ruff: noqa: A003


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


class SensingAgentConfig(AgentConfig):
    R"""Configuration object for a :class:`.SensingAgent`."""

    sensor: SensorConfig
    R""":class:`.SensorConfig`: defines the sensor object of this sensing agent."""
