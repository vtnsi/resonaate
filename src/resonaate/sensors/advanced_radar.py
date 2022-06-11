"""Defines the :class:`.AdvRadar` sensor class."""
# Local Imports
from .radar import Radar

ADV_RADAR_MIN_DETECTABLE_VISMAG = 25.0  # Default minimum observable visual magnitude (unitless)
ADV_RADAR_MIN_RANGE = 0  # Default minimum range an RSO must be at to be observable (km)
ADV_RADAR_MAX_RANGE = 10000  # Default maximum range an RSO must be at to be observable (km)
ADV_RADAR_DEFAULT_FOV = 179  # Default Field of View of an advanced radar sensor (degrees)


class AdvRadar(Radar):
    """Advanced radar sensor class.

    The Advanced Radar Sensor Class (Radar) is used to model four dimensional radar sensors that
    take range, azimuth, elevation, and range rate measurements for each observation. This is a
    specialization of the :class:`.Radar` class, overriding methods for adding extra measurements
    into the observation.
    """
