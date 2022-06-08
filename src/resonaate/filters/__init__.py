# Standard Imports
from copy import deepcopy
# Third Party Imports
from numpy import ndarray
# RESONAATE Imports
from .unscented_kalman_filter import UnscentedKalmanFilter
from ..dynamics.dynamics_base import Dynamics


def kalmanFilterFactory(configuration):
    """Build a :class:`.SequentialFilter` object for target state estimation.

    Args:
        configuration (``dict``): describes the filter to be built

    Returns:
        :class:`.SequentialFilter`: constructed filter object
    """
    # Check types for already constructed objects
    if not isinstance(configuration["dynamics"], Dynamics):
        raise TypeError("Invalid type for 'dynamics': {0}".format(type(configuration["dynamics"])))
    if not isinstance(configuration["process_noise"], ndarray):
        raise TypeError("Invalid type for 'process_noise': {0}".format(type(configuration["process_noise"])))

    # Create the base estimation filter for nominal operation
    config_copy = deepcopy(configuration)
    if config_copy.pop("filter_type").lower() in ("ukf", "unscented_kalman_filter"):
        nominal_filter = UnscentedKalmanFilter(
            config_copy.pop("dynamics"),
            config_copy.pop("process_noise"),
            **config_copy
        )
    else:
        raise ValueError(configuration["filter_type"])

    return nominal_filter
