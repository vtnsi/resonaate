"""Submodule defining the objects listed in the 'engines' configuration section."""
from __future__ import annotations

# Standard Library Imports
from dataclasses import dataclass

# Local Imports
from ...common.labels import SensorLabel
from .agent_config import SensingAgentConfig, TargetAgentConfig
from .base import ConfigError, ConfigObject, ConfigObjectList
from .decision_config import DecisionConfig
from .reward_config import RewardConfig


@dataclass
class EngineConfig(ConfigObject):
    """Defines the structure for an object defined in the 'engines' configuration section."""

    unique_id: int
    """``int``: Unique ID for the defined engine."""

    reward: RewardConfig | dict
    """:class:`.RewardConfig`: Reward configuration section for the defined engine."""

    decision: DecisionConfig | dict
    """:class:`.DecisionConfig`: Decision configuration section for the defined engine."""

    sensors: ConfigObjectList[SensingAgentConfig] | list[SensingAgentConfig | dict]
    """``list``: :class:`.SensingAgentConfig` objects that this engine can task."""

    targets: ConfigObjectList[TargetAgentConfig] | list[TargetAgentConfig | dict]
    """``list``: :class:`.TargetAgentConfig` objects that this engine can be task against."""

    def __post_init__(self):
        """Runs after the object is initialized."""
        if isinstance(self.reward, dict):
            self.reward = RewardConfig(**self.reward)

        if isinstance(self.decision, dict):
            self.decision = DecisionConfig(**self.decision)

        self.sensors = ConfigObjectList("sensors", SensingAgentConfig, self.sensors)
        self.targets = ConfigObjectList("targets", TargetAgentConfig, self.targets)

        # [NOTE]: Only Advanced Radar can used with an AllVisibleDecision type.
        if self.decision.name == "AllVisibleDecision":
            for sensor in self.sensors:
                if sensor.sensor.type != SensorLabel.ADV_RADAR:
                    err = "Only AdvRadar sensors can use the AllVisibleDecision"
                    err += f": sensor {sensor.id} is {sensor.sensor.type}"
                    raise ConfigError(self.__class__.__name__, err)
