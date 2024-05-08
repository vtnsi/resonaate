"""Defines the :class:`.AdvRadar` sensor class."""

from __future__ import annotations

# Standard Library Imports
from typing import TYPE_CHECKING

# Local Imports
from .radar import Radar

# Type Checking Imports
if TYPE_CHECKING:
    # Standard Library Imports
    from typing import Any

ADV_RADAR_DEFAULT_FOV: dict[str, Any] = {
    "fov_shape": "conic",
    "cone_angle": 179.0,
}
"""``dict``: Default Field of View (conic) of an advanced radar sensor, degrees."""


class AdvRadar(Radar):
    """Advanced radar sensor class.

    The Advanced Radar Sensor Class (Radar) is used to model four dimensional radar sensors that
    take range, azimuth, elevation, and range rate measurements for each observation. This is a
    specialization of the :class:`.Radar` class, overriding methods for adding extra measurements
    into the observation.

    References:
        #  :cite:t:`vallado_2016_aiaa_covariance`
    """
