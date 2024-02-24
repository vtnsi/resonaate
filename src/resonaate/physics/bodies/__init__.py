"""Contains classes defining Solar System bodies and their properties."""

from __future__ import annotations

# Local Imports
from .earth import Earth
from .third_body import Jupiter, Moon, Saturn, Sun, Venus

__all__ = ["Earth", "Jupiter", "Moon", "Saturn", "Sun", "Venus"]
