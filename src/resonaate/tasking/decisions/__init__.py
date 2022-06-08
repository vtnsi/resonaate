# RESONAATE Imports
from .decision_base import Decision as _BaseDecision
from .decisions import MunkresDecision, MyopicNaiveGreedyDecision, RandomDecision, AllVisibleDecision


# Register each reward class to global registry
_BaseDecision.register("MunkresDecision", MunkresDecision)
_BaseDecision.register("MyopicNaiveGreedyDecision", MyopicNaiveGreedyDecision)
_BaseDecision.register("RandomDecision", RandomDecision)
_BaseDecision.register("AllVisibleDecision", AllVisibleDecision)


def decisionFactory(configuration):
    """Build a :class:`.Decision` object from a configuration dict.

    Args:
        configuration (``dict``): describes the decision to be built

    Returns:
        :class:`.Decision`: constructed decision object
    """
    return _BaseDecision.REGISTRY.get(configuration["name"])(**configuration["parameters"])
