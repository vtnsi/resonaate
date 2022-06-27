# RESONAATE Imports
# try:
#     # RESONAATE Imports
#     # from resonaate.physics.sensor_utils import (
#     #     apparentVisualMagnitude,
#     #     calculateIncidentSolarFlux,
#     #     calculatePhaseAngle,
#     #     calculateRadarCrossSection,
#     #     calculateSunVizFraction,
#     #     checkGroundSensorLightingConditions,
#     #     checkSpaceSensorLightingConditions,
#     #     getEarthLimbConeAngle,
#     #     getWavelengthFromString,
#     #     lambertianPhaseFunction,
#     #     lineOfSight,
#     # )
# except ImportError as error:
#     raise Exception(f"Please ensure you have appropriate packages installed:\n {error}") from error
# Local Imports
# Testing Imports
from ..conftest import BaseTestCase


class TestSensorUtils(BaseTestCase):
    """Test cases for validating the `physics.sensor_utils` package."""

    def testApparentVisualMagnitude(self):
        """Test apparentVisualMagnitude()."""
