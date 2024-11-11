"""Submodule defining the 'decision' configuration section."""

from __future__ import annotations

# Standard Library Imports
from typing import Annotated, Literal, Optional, Union

# Third Party Imports
from pydantic import BaseModel, Field

# Local Imports
from ...common.labels import DecisionLabel


class MunkresDecisionConfig(BaseModel):
    """Configuration section defining parameters for the munkres decision making algorithm."""

    name: Literal[DecisionLabel.MUNKRES] = DecisionLabel.MUNKRES  # type: ignore
    """``str``: Name of this decision making algorithm."""


class MyopicNaiveGreedyDecisionConfig(BaseModel):
    """Configuration section defining parameters for the myopic naive greedy decision making algorithm."""

    name: Literal[DecisionLabel.MYOPIC_NAIVE_GREEDY] = DecisionLabel.MYOPIC_NAIVE_GREEDY  # type: ignore
    """``str``: Name of this decision making algorithm."""


class RandomDecisionConfig(BaseModel):
    """Configuration section defining parameters for the random decision making algorithm."""

    name: Literal[DecisionLabel.RANDOM] = DecisionLabel.RANDOM  # type: ignore
    """``str``: Name of this decision making algorithm."""

    seed: Optional[int] = None  # noqa: UP007
    """``int``: Seed for pseudo-random number generator."""


class AllVisibleDecision(BaseModel):
    """Configuration section defining parameters for the 'all visible' decision making algorithm."""

    name: Literal[DecisionLabel.ALL_VISIBLE] = DecisionLabel.ALL_VISIBLE  # type: ignore
    """``str``: Name of this decision making algorithm."""


DecisionConfig = Annotated[
    Union[
        MunkresDecisionConfig,
        MyopicNaiveGreedyDecisionConfig,
        RandomDecisionConfig,
        AllVisibleDecision,
    ],
    Field(..., discriminator="name"),
]
"""Annotated[Union]: Discriminated union defining valid decision making configurations."""
