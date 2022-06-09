# Standard Library Imports
from copy import deepcopy

# Third Party Imports
import numpy as np

try:
    # RESONAATE Imports
    from resonaate.estimation import (
        VALID_ADAPTIVE_ESTIMATION_LABELS,
        VALID_FILTER_LABELS,
        VALID_MANEUVER_DETECTION_LABELS,
        AdaptiveFilter,
        ManeuverDetection,
        SequentialFilter,
        adaptiveEstimationFactory,
        maneuverDetectionFactory,
        sequentialFilterFactory,
    )
    from resonaate.scenario.config.estimation_config import (
        AdaptiveEstimationConfig,
        ManeuverDetectionConfig,
        SequentialFilterConfig,
    )
except ImportError as error:
    raise Exception(f"Please ensure you have appropriate packages installed:\n {error}") from error
# Third Party Imports
# Testing Imports
import pytest

MANEUVER_DETECTION_CONFIG = {
    "threshold": 0.01,
    "parameters": {},
}


ESTIMATION_CONFIG = {
    "sequential_filter": {
        "name": "unscented_kalman_filter",
        "parameters": {},
        "dynamics_model": "special_perturbations",
        "maneuver_detection": None,
        "adaptive_estimation": False,
    },
    "adaptive_filter": {
        "name": "smm",
        "orbit_determination": "lambert_universal",
        "model_interval": 60,
        "stacking_method": "eci_stack",
        "observation_window": 1,
        "prune_threshold": 1e-10,
        "prune_percentage": 0.995,
    },
}


TGT_ID = 10000
INITIAL_TIME = 0.0
VISUAL_CROSS_SECTION = 25.0
EST_X = np.array([1000, 2000, 4000, -5, 2, 1])
EST_P = np.eye(6) * 30
Q_MATRIX = np.eye(6) * 50


@pytest.mark.parametrize("sequential_filter_type", VALID_FILTER_LABELS)
def testSequentialFilterFactory(sequential_filter_type, dynamics):
    """Tests dynamically creating filter objects."""
    # Create config dict
    config = deepcopy(ESTIMATION_CONFIG["sequential_filter"])
    config["name"] = sequential_filter_type
    if sequential_filter_type == "ukf":
        config["parameters"] = {
            "alpha": 0.01,
            "beta": 2,
        }
    # Create config object
    estimation_config = SequentialFilterConfig()
    estimation_config.readConfig(config)
    # Call factory function
    filter_obj = sequentialFilterFactory(
        estimation_config, TGT_ID, INITIAL_TIME, EST_X, EST_P, dynamics, Q_MATRIX
    )
    assert isinstance(filter_obj, SequentialFilter)


def testSequentialFilterFactoryError(dynamics):
    """Tests catching errors for bad filter types."""
    config = deepcopy(ESTIMATION_CONFIG["sequential_filter"])
    config["name"] = "ukf"
    # Create config object
    estimation_config = SequentialFilterConfig()
    estimation_config.readConfig(config)
    estimation_config._name._setting = "invlaid_name"  # pylint: disable=protected-access
    # Call factory function
    error_msg = f"Invalid filter type: {estimation_config.name}"
    with pytest.raises(ValueError, match=error_msg):
        _ = sequentialFilterFactory(
            estimation_config, TGT_ID, INITIAL_TIME, EST_X, EST_P, dynamics, Q_MATRIX
        )


@pytest.mark.parametrize("detection_method", VALID_MANEUVER_DETECTION_LABELS)
def testManeuverDetectionFactory(detection_method):
    """Tests dynamically creating filter objects."""
    # Create config dict
    config = deepcopy(MANEUVER_DETECTION_CONFIG)
    config["name"] = detection_method
    # Create config object
    maneuver_det_config = ManeuverDetectionConfig()
    maneuver_det_config.readConfig(config)
    # Call factory function
    maneuver_detection = maneuverDetectionFactory(maneuver_det_config)
    assert isinstance(maneuver_detection, ManeuverDetection)

    config["name"] = None
    # Create config object
    maneuver_det_config = ManeuverDetectionConfig()
    maneuver_det_config.readConfig(config)
    # Call factory function
    maneuver_detection = maneuverDetectionFactory(maneuver_det_config)
    assert maneuver_detection is None

    config["name"] = "standard_nis"
    # Create config object
    maneuver_det_config = ManeuverDetectionConfig()
    maneuver_det_config.readConfig(config)
    maneuver_det_config._name._setting = "invalid_name"  # pylint: disable=protected-access
    # Call factory function
    error_msg = f"Invalid maneuver detection type: {maneuver_det_config.name}"
    with pytest.raises(ValueError, match=error_msg):
        _ = maneuverDetectionFactory(maneuver_det_config)


@pytest.mark.parametrize("adaptive_filter_type", VALID_ADAPTIVE_ESTIMATION_LABELS)
def testAdaptiveFilterFactory(adaptive_filter_type, dynamics):
    """Tests dynamically creating adaptive filter objects."""
    # Create config dict
    config = deepcopy(ESTIMATION_CONFIG["adaptive_filter"])
    config["name"] = adaptive_filter_type
    # Create config object
    estimation_config = AdaptiveEstimationConfig()
    estimation_config.readConfig(config)

    config2 = deepcopy(ESTIMATION_CONFIG["sequential_filter"])
    config2["name"] = "ukf"
    sequential_config = SequentialFilterConfig()
    sequential_config.readConfig(config2)

    sequential_filter = sequentialFilterFactory(
        sequential_config, TGT_ID, INITIAL_TIME, EST_X, EST_P, dynamics, Q_MATRIX
    )

    config3 = deepcopy(MANEUVER_DETECTION_CONFIG)
    config3["name"] = "standard_nis"
    # Create config object
    maneuver_det_config = ManeuverDetectionConfig()
    maneuver_det_config.readConfig(config3)
    # Call factory function
    maneuver_detection = maneuverDetectionFactory(maneuver_det_config)

    sequential_filter.maneuver_detection = maneuver_detection
    sequential_filter.maneuver_detection.metric = 1

    # Call factory function
    filter_obj = adaptiveEstimationFactory(estimation_config, sequential_filter, time_step=300)
    assert isinstance(filter_obj, AdaptiveFilter)

    # Create config object
    estimation_config = AdaptiveEstimationConfig()
    estimation_config.readConfig(config)
    estimation_config._name._setting = "invalid_name"  # pylint: disable=protected-access
    # Call factory function
    error_msg = f"Invalid adaptive estimation type: {estimation_config.name}"
    with pytest.raises(ValueError, match=error_msg):
        _ = adaptiveEstimationFactory(estimation_config, sequential_filter, time_step=300)
