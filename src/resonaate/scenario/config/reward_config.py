"""Submodule defining the 'reward' configuration section."""
from __future__ import annotations

# Standard Library Imports
from dataclasses import dataclass, field
from typing import ClassVar

# Local Imports
from ...tasking.metrics import VALID_METRICS
from ...tasking.rewards import VALID_REWARDS
from .base import ConfigObject, ConfigObjectList, ConfigValueError


@dataclass
class MetricConfig(ConfigObject):
    """Define a metric function config."""

    name: str
    """``str``: Name of this metric function."""

    parameters: dict = field(default_factory=dict)
    """``dict``: Parameters for the metric function."""

    def __post_init__(self):
        """Runs after the object is initialized."""
        if self.name not in VALID_METRICS:
            raise ConfigValueError("name", self.name, VALID_METRICS)


@dataclass
class RewardConfig(ConfigObject):
    """Configuration section defining several reward-based options."""

    CONFIG_LABEL: ClassVar[str] = "reward"
    """``str``: Key where settings are stored in the configuration dictionary."""

    name: str
    """``str``: Name of this reward function."""

    metrics: ConfigObjectList[MetricConfig] | list[MetricConfig | dict]
    """``list``: :class:`.MetricConfig` objects for calculating the reward."""

    parameters: dict = field(default_factory=dict)
    """``dict``: Parameters for the reward function."""

    def __post_init__(self):
        """Runs after the object is initialized."""
        if self.name not in VALID_REWARDS:
            raise ConfigValueError("name", self.name, VALID_REWARDS)

        self.metrics = ConfigObjectList("metrics", MetricConfig, self.metrics)
