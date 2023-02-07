from __future__ import annotations

# Third Party Imports
import numpy as np
import pytest

# RESONAATE Imports
from resonaate.estimation.maneuver_detection import FadingMemoryNis, SlidingNis, StandardNis

MANEUVER_DETECTION_METHODS = (StandardNis, SlidingNis, FadingMemoryNis)


NOT_DETECTABLE = [  # residuals, innov covariance
    (
        np.array([-9.16298020e-06, -6.63225061e-06]),
        np.array([[2.40416348e-11, -3.50156023e-21], [-3.50156023e-21, 2.37368421e-11]]),
    ),
    (
        np.array([3.43452752e-06, 6.18377937e-06]),
        np.array([[2.40400014e-11, -1.43073874e-20], [-1.43073874e-20, 2.37368425e-11]]),
    ),
    (
        np.array([5.33564470e-07, 2.07681348e-06]),
        np.array([[2.40400017e-11, 6.76684976e-21], [6.76684976e-21, 2.37368423e-11]]),
    ),
    (
        np.array([-5.84733223e-06, -2.22445282e-06]),
        np.array([[2.40399995e-11, 1.32166211e-21], [1.32166211e-21, 2.37368420e-11]]),
    ),
]


DETECTABLE = [  # residuals, innov covariance
    (
        np.array([-0.0018326, -0.00132645]),
        np.array([[2.40416348e-11, -3.50156023e-21], [-3.50156023e-21, 2.37368421e-11]]),
    ),
    (
        np.array([2.87689807e-05, -3.57298192e-07]),
        np.array([[2.40400261e-11, -2.63891849e-21], [-2.63891849e-21, 2.37368498e-11]]),
    ),
    (
        np.array([7.25924780e-06, 2.04718055e-06]),
        np.array([[2.88999668e-12, -9.72670601e-22], [-9.72670601e-22, 2.58684259e-12]]),
    ),
    (
        np.array([0.00022723, -0.00025578]),
        np.array([[5.40652784e-09, -4.05524870e-19], [-4.05524973e-19, 2.37124397e-09]]),
    ),
]


def testManeuverDetectionClassInits():
    """Test a Maneuver detection inits."""
    # Standard constructors
    _ = StandardNis(0.01)
    _ = SlidingNis(0.01, window_size=4)
    _ = FadingMemoryNis(0.01, delta=0.5)
    # Use default args
    _ = SlidingNis(0.01)
    _ = FadingMemoryNis(0.01)

    # Test bad parameters
    sliding_err = r"Invalid value for SlidingNis discount factor, window_size: [-]*\d+"
    with pytest.raises(ValueError, match=sliding_err):
        _ = SlidingNis(0.01, window_size=0)

    with pytest.raises(ValueError, match=sliding_err):
        _ = SlidingNis(0.01, window_size=-1)

    fading_err = r"Invalid value for FadingMemoryNis discount factor, delta: [-]*\d+"
    with pytest.raises(ValueError, match=fading_err):
        _ = FadingMemoryNis(0.01, delta=0)

    with pytest.raises(ValueError, match=fading_err):
        _ = FadingMemoryNis(0.01, delta=1)

    with pytest.raises(ValueError, match=fading_err):
        _ = FadingMemoryNis(0.01, delta=1.1)

    with pytest.raises(ValueError, match=fading_err):
        _ = FadingMemoryNis(0.01, delta=-1.0)


@pytest.mark.parametrize("detection_class", MANEUVER_DETECTION_METHODS)
def testNoManeuverDetection(detection_class):
    """Test that does not result in a maneuver detection."""
    alpha = 0.05
    detection_method = detection_class(alpha)
    for res, cvr in NOT_DETECTABLE:
        assert not detection_method(res, cvr)


@pytest.mark.parametrize("detection_class", MANEUVER_DETECTION_METHODS)
def testManeuverDetection(detection_class):
    """Test that does result in a maneuver detection."""
    alpha = 0.05
    detection_method = detection_class(alpha)
    for res, cvr in DETECTABLE:
        assert detection_method(res, cvr)
