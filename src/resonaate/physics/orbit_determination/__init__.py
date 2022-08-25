"""Orbit Determination algorithms."""
from __future__ import annotations

# Standard Library Imports
from typing import TYPE_CHECKING, Callable

# Third Party Imports
from numpy import ndarray

# Local Imports
from ..time.stardate import ScenarioTime

if TYPE_CHECKING:
    # Third Party Imports
    from typing_extensions import TypeAlias


OrbitDeterminationFunction: TypeAlias = Callable[[ndarray, ndarray, ScenarioTime, int], ndarray]
