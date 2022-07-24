"""Defines the decisions algorithms available in RESONAATE."""
from __future__ import annotations

# Standard Library Imports
from typing import TYPE_CHECKING

# Local Imports
from .decision_base import Decision
from .decisions import (
    AllVisibleDecision,
    MunkresDecision,
    MyopicNaiveGreedyDecision,
    RandomDecision,
)

# Type Checking Imports
if TYPE_CHECKING:
    # Local Imports
    from ...scenario.config.decision_config import DecisionConfig


# Register each reward class to global registry
Decision.register(MunkresDecision)
Decision.register(MyopicNaiveGreedyDecision)
Decision.register(RandomDecision)
Decision.register(AllVisibleDecision)


VALID_DECISIONS: list[str] = list(Decision.REGISTRY.keys())
"""``list``: List of valid decision labels."""


def decisionFactory(configuration: DecisionConfig) -> Decision:
    """Build a :class:`.Decision` object from a configuration dict.

    Args:
        configuration (:class:`.DecisionConfig`): describes the decision to be built.

    Returns:
        :class:`.Decision`: constructed decision object.
    """
    return Decision.REGISTRY.get(configuration.name)(**configuration.parameters)
