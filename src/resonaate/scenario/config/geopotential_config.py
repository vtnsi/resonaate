"""Submodule defining the 'geopotential' configuration section."""

from __future__ import annotations

# Third Party Imports
from pydantic import BaseModel, Field

# Local Imports
from ...common.labels import GeopotentialModel


class GeopotentialConfig(BaseModel):
    """Configuration section defining several geopotential-based options."""

    model: GeopotentialModel = GeopotentialModel.EGM96
    """``str``: Model file used to define the Earth's gravity model."""

    degree: int = Field(default=4, ge=0, le=80)
    """``int``: Degree of the Earth's gravity model."""

    order: int = Field(default=4, ge=0, le=80)
    """``int``: Order of the Earth's gravity model."""
