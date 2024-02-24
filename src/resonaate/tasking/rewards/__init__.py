"""Defines the reward functions used to quantify tasking solutions."""

from __future__ import annotations

# Standard Library Imports
from typing import TYPE_CHECKING

# Local Imports
from ..metrics.metric_base import Metric
from .reward_base import Reward
from .rewards import CombinedReward, CostConstrainedReward, SimpleSummationReward

# Type Checking Imports
if TYPE_CHECKING:
    # Local Imports
    from ...scenario.config.reward_config import RewardConfig


# Register each reward class to global registry
Reward.register(CostConstrainedReward)
Reward.register(SimpleSummationReward)
Reward.register(CombinedReward)


VALID_REWARDS: list[str] = list(Reward.REGISTRY.keys())
"""``list``: List of valid reward labels."""


def rewardsFactory(configuration: RewardConfig) -> Reward:
    """Build a :class:`.Reward` object from a configuration dict.

    Args:
        configuration (RewardConfig): describes the reward to be built

    Returns:
        :class:`.Reward`: constructed reward object
    """
    metrics_config = configuration.metrics
    metrics: list[Metric] = [
        Metric.REGISTRY[metric.name](**metric.parameters) for metric in metrics_config
    ]

    return Reward.REGISTRY[configuration.name](metrics, **configuration.parameters)
