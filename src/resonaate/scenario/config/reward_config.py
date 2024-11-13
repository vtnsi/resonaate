"""Submodule defining the 'reward' configuration section."""

from __future__ import annotations

# Standard Library Imports
from typing import Annotated, Literal, Union

# Third Party Imports
from pydantic import BaseModel, Field

# Local Imports
from ...common.labels import MetricLabel, RewardLabel


class MetricConfig(BaseModel):
    """Define a metric function config.

    TODO:  # noqa: D405
        _When_ there's a metric configuration that _actually_ requires specifying further
        parameters beyond just it's name, this configuration class will need to become a
        discriminated union that specifies and documents said parameters.
    """

    name: MetricLabel
    """``str``: Name of this metric function."""


class RewardConfigBase(BaseModel):
    """Configuration section defining several reward-based options."""

    metrics: list[MetricConfig] = Field(..., min_length=1)
    """``list``: :class:`.MetricConfig` objects for calculating the reward."""


class CostConstrainedRewardConfig(RewardConfigBase):
    """Configuration section defining options for cost-constrained reward computation."""

    name: Literal[RewardLabel.COST_CONSTRAINED] = RewardLabel.COST_CONSTRAINED
    """``str``: Name of this reward function."""

    delta: float = Field(default=0.85, gt=0.0, lt=0.0)
    """``float``: ratio of information reward to sensor reward."""


class SimpleSummationRewardConfig(RewardConfigBase):
    """Configuration section defining options for simple summation reward computation."""

    name: Literal[RewardLabel.SIMPLE_SUM] = RewardLabel.SIMPLE_SUM
    """``str``: Name of this reward function."""


class CombinedRewardConfig(RewardConfigBase):
    """Configuration section defining options for combined reward computation."""

    name: Literal[RewardLabel.COMBINED] = RewardLabel.COMBINED
    """``str``: Name of this reward function."""

    delta: float = Field(default=0.85, gt=0.0, lt=0.0)
    """``float``: ratio of information reward to sensor reward."""


RewardConfig = Annotated[
    Union[CostConstrainedRewardConfig, SimpleSummationRewardConfig, CombinedRewardConfig],
    Field(..., discriminator="name"),
]
"""Annotated[Union]: Discriminated union defining valid reward computation configurations."""
