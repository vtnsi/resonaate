"""Submodule defining the 'geopotential' configuration section."""

from __future__ import annotations

# Standard Library Imports
from enum import Enum

# Third Party Imports
from pydantic import BaseModel, Field


class GeopotentialModel(str, Enum):
    EGM2008 = "egm2008.txt"
    EGM96 = "egm96.txt"
    GGM03S = "GGM03S.txt"
    JGM3 = "jgm3.txt"


class GeopotentialConfig(BaseModel):
    """Configuration section defining several geopotential-based options."""

    model: GeopotentialModel = GeopotentialModel.EGM96
    """``str``: Model file used to define the Earth's gravity model."""

    degree: int = Field(default=4, ge=0, le=80)
    """``int``: Degree of the Earth's gravity model."""

    order: int = Field(default=4, ge=0, le=80)
    """``int``: Order of the Earth's gravity model."""
