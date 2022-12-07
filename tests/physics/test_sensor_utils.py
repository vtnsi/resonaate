from __future__ import annotations

# Third Party Imports
from numpy import array, isclose

# RESONAATE Imports
from resonaate.physics.sensor_utils import (
    apparentVisualMagnitude,
    calculateIncidentSolarFlux,
    calculatePhaseAngle,
    calculateSunVizFraction,
    lambertianPhaseFunction,
)

VISUAL_CROSS_SECTION = 25.0
MASS = 100
REFLECTIVITY = 0.21
SOLAR_PHASE_ANGLE = 0.5
NORM_BORESIGHT = 6371
SUN_POSITION = array([1.47199372e08, 2.35328247e07, 1.02011844e07])
RSO_POSITION = array([-6218.88151713, -4625.88230867, 802.87401975])
SENSOR_POSITION = array([4221.25454032, -3223.82650314, 3521.91123676])


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
    assert isclose(flux, 0.0)


def testCalculatePhaseAngle():
    """Test calculatePhaseAngle()."""
    phase = calculatePhaseAngle(SUN_POSITION, RSO_POSITION, SENSOR_POSITION)
    assert isclose(phase, 0.1859393122433178)


def testCalculateSunVizFraction():
    """Test calculateSunVizFraction()."""
    fraction = calculateSunVizFraction(RSO_POSITION, SUN_POSITION)
    assert isclose(fraction, 0.0)


def testLambertianPhaseFunction():
    """Test lambertianPhaseFunction()."""
    phase = lambertianPhaseFunction(SOLAR_PHASE_ANGLE)
    assert isclose(phase, 0.18897354431642885)
