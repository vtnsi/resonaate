"""Submodule defining the objects listed in the 'engines' configuration section."""

# ruff: noqa: UP007, TCH001

from __future__ import annotations

# Third Party Imports
from pydantic import BaseModel, Field, model_validator
from typing_extensions import Self

# Local Imports
from ...common.labels import SensorLabel
from .agent_config import AgentConfig, SensingAgentConfig
from .decision_config import DecisionConfig
from .reward_config import RewardConfig


class EngineConfig(BaseModel):
    """Defines the structure for an object defined in the 'engines' configuration section."""

    unique_id: int
    """``int``: Unique ID for the defined engine."""

    reward: RewardConfig
    """:class:`.RewardConfig`: Reward configuration section for the defined engine."""

    decision: DecisionConfig
    """:class:`.DecisionConfig`: Decision configuration section for the defined engine."""

    sensors: list[SensingAgentConfig] = Field(..., min_length=1)
    """``list``: :class:`.SensingAgentConfig` objects that this engine can task."""

    targets: list[AgentConfig] = Field(..., min_length=1)
    """``list``: :class:`.AgentConfig` objects that this engine can be task against."""

    @model_validator(mode="after")
    def all_viz_compatibility(self) -> Self:
        """Ensure the ``AllVisibleDecision`` algorithm is only applied to advanced radar sensors."""
        # [NOTE]: Only Advanced Radar can used with an AllVisibleDecision type.
        if self.decision.name == "AllVisibleDecision":
            for sensor in self.sensors:
                if sensor.sensor.type != SensorLabel.ADV_RADAR:
                    err = "Only AdvRadar sensors can use the AllVisibleDecision"
                    err += f": sensor {sensor.id} is {sensor.sensor.type}"
                    raise ValueError(err)
        return self
