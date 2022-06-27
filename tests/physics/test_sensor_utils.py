# RESONAATE Imports
try:
    # RESONAATE Imports
    from resonaate.physics.sensor_utils import (
        apparentVisualMagnitude,
        calculateIncidentSolarFlux,
        calculatePhaseAngle,
        calculateRadarCrossSection,
        calculateSunVizFraction,
        checkGroundSensorLightingConditions,
        checkSpaceSensorLightingConditions,
        getEarthLimbConeAngle,
        getWavelengthFromString,
        lambertianPhaseFunction,
        lineOfSight,
    )
except ImportError as error:
    raise Exception(f"Please ensure you have appropriate packages installed:\n {error}") from error
# Local Imports
# Testing Imports
from ..conftest import BaseTestCase


class TestSensorUtils(BaseTestCase):
    """Test cases for validating the `physics.sensor_utils` package."""

    def testApparentVisualMagnitude(self):
        """Test apparentVisualMagnitude()."""

    def testCalculateIncidentSolarFlux(self):
        """Test calculateIncidentSolarFlux()."""

    def testCalculatePhaseAngle(self):
        """Test calculatePhaseAngle()."""

    def testCalculateRadarCrossSection(self):
        """Test calculateRadarCrossSection()."""

    def testCalculateSunVizFraction(self):
        """Test calculateSunVizFraction()."""

    def testCheckGroundSensorLightingConditions(self):
        """Test checkGroundSensorLightingConditions()."""

    def testCheckSpaceSensorLightingConditions(self):
        """Test checkSpaceSensorLightingConditions()."""

    def testGetEarthLimbConeAngle(self):
        """Test getEarthLimbConeAngle()."""

    def testGetWavelengthFromString(self):
        """Test getWavelengthFromString()."""

    def testLambertianPhaseFunction(self):
        """Test lambertianPhaseFunction()."""

    def testLineOfSight(self):
        """Test lineOfSight()."""
