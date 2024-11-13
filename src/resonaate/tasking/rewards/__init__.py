"""Defines the reward functions used to quantify tasking solutions."""

from __future__ import annotations

# Standard Library Imports
from typing import TYPE_CHECKING

# Local Imports
from ...common.labels import RewardLabel
from ..metrics import _METRIC_MAPPING
from .rewards import CombinedReward, CostConstrainedReward, SimpleSummationReward

# Type Checking Imports
if TYPE_CHECKING:
    # Local Imports
    from ...scenario.config.reward_config import RewardConfig
    from ..metrics.metric_base import Metric
    from .reward_base import Reward


_REWARD_MAPPING: dict[RewardLabel, Reward] = {
    RewardLabel.COST_CONSTRAINED: CostConstrainedReward,
    RewardLabel.SIMPLE_SUM: SimpleSummationReward,
    RewardLabel.COMBINED: CombinedReward,
}
"""dict[MetricLabel, Reward]: Maps enumerated reward label to corresponding class."""


def rewardsFactory(configuration: RewardConfig) -> Reward:
    """Build a :class:`.Reward` object from a configuration dict.

    Args:
        configuration (RewardConfig): describes the reward to be built

    Returns:
        :class:`.Reward`: constructed reward object
    """
    metrics_config = configuration.metrics
    metrics: list[Metric] = [
        _METRIC_MAPPING[metric.name]() for metric in metrics_config
    ]

    return _REWARD_MAPPING[configuration.name].fromConfig(metrics, configuration)
