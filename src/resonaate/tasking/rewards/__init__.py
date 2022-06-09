"""Defines the reward functions used to quantify tasking solutions."""
# RESONAATE Imports
from .reward_base import Reward as _BaseReward
from .rewards import CostConstrainedReward, SimpleSummationReward, CombinedReward
from ..metrics.metric_base import Metric

# Register each reward class to global registry
_BaseReward.register("CostConstrainedReward", CostConstrainedReward)
_BaseReward.register("SimpleSummationReward", SimpleSummationReward)
_BaseReward.register("CombinedReward", CombinedReward)

VALID_REWARDS = list(_BaseReward.REGISTRY.keys())
"""list: List of valid reward labels."""


def rewardsFactory(configuration):
    """Build a :class:`.Reward` object from a configuration dict.

    Args:
        configuration (RewardConfig): describes the reward to be built

    Returns:
        :class:`.Reward`: constructed reward object
    """
    metrics_config = configuration.metrics
    metrics = [Metric.REGISTRY[metric.name](**metric.parameters) for metric in metrics_config]

    return _BaseReward.REGISTRY[configuration.name](
        metrics,
        **configuration.parameters
    )
