"""Defines the decisions algorithms available in RESONAATE."""

from __future__ import annotations

# Standard Library Imports
from typing import TYPE_CHECKING

# Local Imports
from ...common.labels import DecisionLabel
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
    from .decision_base import Decision


_DECISION_MAPPING: dict[DecisionLabel, Decision] = {
    DecisionLabel.MUNKRES: MunkresDecision,
    DecisionLabel.MYOPIC_NAIVE_GREEDY: MyopicNaiveGreedyDecision,
    DecisionLabel.RANDOM: RandomDecision,
    DecisionLabel.ALL_VISIBLE: AllVisibleDecision,
}
"""dict[DecisionLabel, Decision]: Maps enumerated decision label to corresponding class."""


def decisionFactory(configuration: DecisionConfig) -> Decision:
    """Build a :class:`.Decision` object from a configuration dict.

    Args:
        configuration (:class:`.DecisionConfig`): describes the decision to be built.

    Returns:
        :class:`.Decision`: constructed decision object.
    """
    return _DECISION_MAPPING[configuration.name].fromConfig(configuration)
