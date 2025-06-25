from __future__ import annotations

# Third Party Imports
import numpy as np
import pytest

# RESONAATE Imports
from resonaate.estimation import (
    AdaptiveFilter,
    ManeuverDetection,
    SequentialFilter,
    adaptiveEstimationFactory,
    maneuverDetectionFactory,
    sequentialFilterFactory,
)
from resonaate.scenario.config import constructFromUnion
from resonaate.scenario.config.estimation_config import (
    AdaptiveEstimationConfig,
    AdaptiveEstimationLabel,
    ManeuverDetectionConfig,
    ManeuverDetectionLabel,
    SequentialFilterConfig,
    SequentialFilterLabel,
    StandardNISConfig,
    UKFConfig,
)

# Local Imports
from ..scenario.config.test_estimation_config import (
    getAdaptiveConfigDict,
    getManeuverDetectionDict,
    getSeqFilterDict,
)

TGT_ID = 10000
INITIAL_TIME = 0.0
VISUAL_CROSS_SECTION = 25.0
EST_X = np.array([1000, 2000, 4000, -5, 2, 1])
EST_P = np.eye(6) * 30
Q_MATRIX = np.eye(6) * 50


@pytest.mark.parametrize("sequential_filter_type", list(SequentialFilterLabel))
def testSequentialFilterFactory(sequential_filter_type, dynamics):
    """Tests dynamically creating filter objects."""
    # Create config
    config = getSeqFilterDict(name=sequential_filter_type)
    estimation_config = constructFromUnion(SequentialFilterConfig, config)
    # Call factory function
    filter_obj = sequentialFilterFactory(
        estimation_config,
        TGT_ID,
        INITIAL_TIME,
        EST_X,
        EST_P,
        dynamics,
        Q_MATRIX,
    )
    assert isinstance(filter_obj, SequentialFilter)


def testSequentialFilterFactoryDupManeuverHandlingError(dynamics):
    """Tests catching errors for setting MMAE and IOD for a single filter."""
    # Mutate bad config
    estimation_config = UKFConfig()
    estimation_config.adaptive_estimation = True
    estimation_config.initial_orbit_determination = True
    # Call factory function
    error_msg = "IOD & MMAE cannot be used at the same time"
    with pytest.raises(ValueError, match=error_msg):
        _ = sequentialFilterFactory(
            estimation_config,
            TGT_ID,
            INITIAL_TIME,
            EST_X,
            EST_P,
            dynamics,
            Q_MATRIX,
        )


@pytest.mark.parametrize("detection_method", list(ManeuverDetectionLabel))
def testManeuverDetectionFactory(detection_method):
    """Tests dynamically creating filter objects."""
    # Create config
    config = getManeuverDetectionDict(name=detection_method)
    maneuver_det_config = constructFromUnion(ManeuverDetectionConfig, config)
    # Call factory function
    maneuver_detection = maneuverDetectionFactory(maneuver_det_config)
    assert isinstance(maneuver_detection, ManeuverDetection)


@pytest.mark.parametrize("_input", [{}, None])
def testManeuverDetectionFactorySparse(_input):
    """Validate that :meth:`.maneuverDetectionFactory()` returns None in appropriate circumstances."""
    assert maneuverDetectionFactory(_input) is None


@pytest.mark.parametrize("adaptive_filter_type", list(AdaptiveEstimationLabel))
def testAdaptiveFilterFactory(adaptive_filter_type, dynamics):
    """Tests dynamically creating adaptive filter objects."""
    config = getAdaptiveConfigDict(name=adaptive_filter_type)
    estimation_config = constructFromUnion(AdaptiveEstimationConfig, config)

    sequential_config = UKFConfig()
    sequential_filter = sequentialFilterFactory(
        sequential_config,
        TGT_ID,
        INITIAL_TIME,
        EST_X,
        EST_P,
        dynamics,
        Q_MATRIX,
    )

    maneuver_det_config = StandardNISConfig()
    maneuver_detection = maneuverDetectionFactory(maneuver_det_config)

    sequential_filter.maneuver_detection = maneuver_detection
    sequential_filter.maneuver_detection.metric = 1

    # Call factory function
    filter_obj = adaptiveEstimationFactory(estimation_config, sequential_filter, time_step=300)
    assert isinstance(filter_obj, AdaptiveFilter)
