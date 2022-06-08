# RESONAATE Imports
from .reward_base import Reward as _BaseReward
from .rewards import CostConstrainedReward, SimpleSummationReward, CombinedReward
from ..metrics.metric_base import Metric

# Register each reward class to global registry
_BaseReward.register("CostConstrainedReward", CostConstrainedReward)
_BaseReward.register("SimpleSummationReward", SimpleSummationReward)
_BaseReward.register("CombinedReward", CombinedReward)


def rewardsFactory(configuration):
    """Build a :class:`.Reward` object from a configuration dict.

    Args:
        configuration (``dict``): describes the reward to be built

    Returns:
        :class:`.Reward`: constructed reward object
    """
    metrics_config = configuration["metrics"]
    metrics = [Metric.REGISTRY[metric["name"]](**metric["parameters"]) for metric in metrics_config]

    return _BaseReward.REGISTRY[configuration["name"]](
        metrics,
        **configuration["parameters"]
    )
