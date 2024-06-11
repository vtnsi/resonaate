"""Submodule defining the 'reward' configuration section."""

from __future__ import annotations

# Third Party Imports
from pydantic import BaseModel, Field, field_validator

# Local Imports
from ...tasking.metrics import VALID_METRICS
from ...tasking.rewards import VALID_REWARDS


class MetricConfig(BaseModel):
    """Define a metric function config."""

    name: str
    """``str``: Name of this metric function."""

    @field_validator('name')
    @classmethod
    def name_must_be_valid(cls, v: str) -> str:
        if v not in VALID_METRICS:
            err = f"Metric '{v}' is not valid."
            raise ValueError(err)
        return v

    parameters: dict = Field(default_factory=dict)
    """``dict``: Parameters for the metric function."""


class RewardConfig(BaseModel):
    """Configuration section defining several reward-based options."""

    name: str
    """``str``: Name of this reward function."""

    @field_validator('name')
    @classmethod
    def name_must_be_valid(cls, v: str) -> str:
        if v not in VALID_REWARDS:
            err = f"Reward '{v}' is not valid."
            raise ValueError(err)
        return v

    metrics: list[MetricConfig]
    """``list``: :class:`.MetricConfig` objects for calculating the reward."""

    parameters: dict = Field(default_factory=dict)
    """``dict``: Parameters for the reward function."""
