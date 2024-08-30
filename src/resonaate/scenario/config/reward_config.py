"""Submodule defining the 'reward' configuration section."""

from __future__ import annotations

# Third Party Imports
from pydantic import BaseModel, Field, field_validator

# Local Imports
from ...common.labels import MetricLabel
from ...tasking.rewards import VALID_REWARDS


class MetricConfig(BaseModel):
    """Define a metric function config.

    TODO:
        _When_ there's a metric configuration that _actually_ requires specifying further
        parameters beyond just it's name, this configuration class will need to become a
        discriminated union that specifies and documents said parameters.
    """

    name: MetricLabel
    """``str``: Name of this metric function."""


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
