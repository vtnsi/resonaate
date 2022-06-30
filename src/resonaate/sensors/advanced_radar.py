"""Defines the :class:`.AdvRadar` sensor class."""
# Local Imports
from .radar import Radar

ADV_RADAR_DEFAULT_FOV = {
    "fov_shape": "conic",
    "cone_angle": 179.0,
}  # Default Field of View of an advanced radar sensor (degrees)


class AdvRadar(Radar):
    """Advanced radar sensor class.

    The Advanced Radar Sensor Class (Radar) is used to model four dimensional radar sensors that
    take range, azimuth, elevation, and range rate measurements for each observation. This is a
    specialization of the :class:`.Radar` class, overriding methods for adding extra measurements
    into the observation.

    References:
        #  :cite:t:`vallado_2016_aiaa_covariance`
    """
