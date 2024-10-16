from __future__ import annotations

# Third Party Imports
import numpy as np
import pytest

# RESONAATE Imports
from resonaate.physics.sensor_utils import (
    FrequencyBand,
    apparentVisualMagnitude,
    calculateIncidentSolarFlux,
    calculatePhaseAngle,
    calculateSunVizFraction,
    getBodyLimbConeAngle,
    lambertianPhaseFunction,
)

VISUAL_CROSS_SECTION = 25.0
MASS = 100
REFLECTIVITY = 0.21
SOLAR_PHASE_ANGLE = 0.5
NORM_BORESIGHT = 6371
SUN_POSITION = np.array([1.47199372e08, 2.35328247e07, 1.02011844e07])
RSO_POSITION = np.array([-6218.88151713, -4625.88230867, 802.87401975])
SENSOR_POSITION = np.array([4221.25454032, -3223.82650314, 3521.91123676])


def testApparentVisualMagnitude():
    """Test that apparentVisualMagnitude function runs."""
    _ = apparentVisualMagnitude(
        VISUAL_CROSS_SECTION,
        REFLECTIVITY,
        lambertianPhaseFunction(SOLAR_PHASE_ANGLE),
        NORM_BORESIGHT,
    )


def testCalculateIncidentSolarFlux():
    """Test calculateIncidentSolarFlux()."""
    flux = calculateIncidentSolarFlux(VISUAL_CROSS_SECTION, RSO_POSITION, SUN_POSITION)
    assert np.isclose(flux, 0.0)


def testCalculatePhaseAngle():
    """Test calculatePhaseAngle()."""
    phase = calculatePhaseAngle(SUN_POSITION, RSO_POSITION, SENSOR_POSITION)
    assert np.isclose(phase, 0.1859393122433178)


def testCalculateSunVizFraction():
    """Test calculateSunVizFraction()."""
    fraction = calculateSunVizFraction(RSO_POSITION, SUN_POSITION)
    assert np.isclose(fraction, 0.0)


def testLambertianPhaseFunction():
    """Test lambertianPhaseFunction()."""
    phase = lambertianPhaseFunction(SOLAR_PHASE_ANGLE)
    assert np.isclose(phase, 0.18897354431642885)


def testGetFrequencyFromString():
    """Test getFrequencyFromString()."""
    frequency_string = "L"
    freq_band = FrequencyBand(frequency_string)
    assert freq_band.mean == 1.5 * 1e9


def testBodyLimbConeAngleBadInputs():
    """Test that invalid inputs to `getBodyLimbConeAngle()` raises a `ValueError`."""
    with pytest.raises(
        ValueError,
        match="Observer distance cannot be less than the celestial body limb.",
    ):
        getBodyLimbConeAngle(2.0, 1.0)


def testBodyLimbConeAngleFarObserver():
    """Test that an infinitely far away observer sees a body limb half cone angle of zero."""
    cone_angle = getBodyLimbConeAngle(1.0, np.inf)
    assert np.isclose(cone_angle, 0.0)


def testBodyLimbConeAngleCloseObserver():
    """Test that an observer on the body sees a half cone angle of 90 degrees."""
    cone_angle = getBodyLimbConeAngle(1.0, 1.0)
    assert np.isclose(cone_angle, np.pi / 2)
