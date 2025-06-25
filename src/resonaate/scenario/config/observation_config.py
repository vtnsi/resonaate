"""Submodule defining the 'observation' configuration section."""

from __future__ import annotations

# Third Party Imports
from pydantic import BaseModel


class ObservationConfig(BaseModel):
    """Configuration section defining several observation-based options."""

    background: bool = True
    """``bool``: whether or not to do field of view on background rso calculations."""

    realtime_observation: bool = True
    """``bool``: whether to generate observations during the simulation."""
