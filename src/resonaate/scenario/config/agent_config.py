"""Module that defines the objects stored in the 'targets' and 'sensors' configuration sections."""

from __future__ import annotations

# Standard Library Imports
from dataclasses import dataclass
from typing import ClassVar

# Local Imports
from .base import ConfigObject
from .platform_config import PlatformConfig
from .sensor_config import SensorConfig
from .state_config import StateConfig

# ruff: noqa: A003


@dataclass
class AgentConfig(ConfigObject):
    R"""Configuration base class defining an agent."""

    # Config label class variable - not used by "dataclass"
    CONFIG_LABEL: ClassVar[str] = "agent"
    R"""``str``: Key where settings are stored in the configuration dictionary."""

    id: int
    R"""``int``: unique ID of the agent."""

    name: str
    R"""``str``: name of the agent."""

    state: StateConfig | dict
    R""":class:`.StateConfig`: defines the location/dynamics of this agent."""

    platform: PlatformConfig | dict
    R""":class:`.PlatformConfig`: defines the behavior/dynamics of this agent."""

    def __post_init__(self):
        R"""Runs after the dataclass is initialized."""
        if isinstance(self.state, dict):
            self.state = StateConfig.fromDict(self.state)

        if isinstance(self.platform, dict):
            self.platform = PlatformConfig.fromDict(self.platform, state=self.state)


@dataclass
class TargetAgentConfig(AgentConfig):
    R"""Configuration object for a target."""

    # Config label class variable - not used by "dataclass"
    CONFIG_LABEL: ClassVar[str] = "target_agent"
    R"""``str``: Key where settings are stored in the configuration dictionary."""


@dataclass
class SensingAgentConfig(AgentConfig):
    R"""Configuration object for a :class:`.SensingAgent`."""

    # Config label class variable - not used by "dataclass"
    CONFIG_LABEL: ClassVar[str] = "sensing_agent"
    R"""``str``: Key where settings are stored in the configuration dictionary."""

    sensor: SensorConfig | dict
    R""":class:`.SensorConfig`: defines the sensor object of this sensing agent."""

    def __post_init__(self):
        R"""Runs after the dataclass is initialized."""
        super().__post_init__()

        if isinstance(self.sensor, dict):
            self.sensor = SensorConfig.fromDict(self.sensor)
