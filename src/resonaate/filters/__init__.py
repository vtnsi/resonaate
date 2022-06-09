"""Contains all classes and functions related to estimation theory.

This includes Kalman filter classes, statistical tests, and debugging utility functions.
"""
# Standard Imports
from copy import deepcopy
# Third Party Imports
from numpy import ndarray
# RESONAATE Imports
from .unscented_kalman_filter import UnscentedKalmanFilter
from ..dynamics.dynamics_base import Dynamics


VALID_FILTER_LABELS = ("ukf", "unscented_kalman_filter")
"""tuple: Collection of valid entries for "filter_type" key in filter configuration dictionary."""


VALID_MANEUVER_DETECTION_LABELS = ('standard_nis', 'sliding_nis', 'fading_memory_nis')
"""tuple: Collection of valid entries for "maneuver_detection_method" key in filter configuration dictionary."""


def kalmanFilterFactory(configuration):
    """Build a :class:`.SequentialFilter` object for target state estimation.

    Args:
        configuration (``dict``): describes the filter to be built

    Returns:
        :class:`.SequentialFilter`: constructed filter object
    """
    # Check types for already constructed objects
    if not isinstance(configuration["dynamics"], Dynamics):
        dynamics_type = type(configuration["dynamics"])
        raise TypeError(f"Invalid type for 'dynamics': {dynamics_type}")
    if not isinstance(configuration["process_noise"], ndarray):
        noise_type = type(configuration["process_noise"])
        raise TypeError(f"Invalid type for 'process_noise': {noise_type}")

    # Create the base estimation filter for nominal operation
    config_copy = deepcopy(configuration)
    if config_copy.pop("filter_type").lower() in VALID_FILTER_LABELS:
        nominal_filter = UnscentedKalmanFilter(
            config_copy.pop("dynamics"),
            config_copy.pop("process_noise"),
            config_copy.pop("maneuver_detection_method"),
            **config_copy
        )
    else:
        raise ValueError(configuration["filter_type"])

    return nominal_filter
