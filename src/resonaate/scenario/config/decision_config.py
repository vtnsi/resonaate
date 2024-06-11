"""Submodule defining the 'decision' configuration section."""

from __future__ import annotations

# Third Party Imports
from pydantic import BaseModel, Field, field_validator

# Local Imports
from ...tasking.decisions import VALID_DECISIONS


class DecisionConfig(BaseModel):
    """Configuration section defining several decision-based options."""

    name: str
    """``str``: Name of this decision function."""

    @field_validator('name')
    @classmethod
    def name_must_be_valid(cls, v: str) -> str:
        if v not in VALID_DECISIONS:
            err = f"Decision '{v}' is not valid."
            raise ValueError(err)
        return v

    parameters: dict = Field(default_factory=dict)
    """``dict``: Parameters for the decision function."""
