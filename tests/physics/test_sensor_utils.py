# Third Party Imports
from numpy import array

try:
    # RESONAATE Imports
    from resonaate.physics.sensor_utils import (
        apparentVisualMagnitude,
        calculateIncidentSolarFlux,
        calculatePhaseAngle,
        calculateSunVizFraction,
        lambertianPhaseFunction,
    )
except ImportError as error:
    raise Exception(f"Please ensure you have appropriate packages installed:\n {error}") from error
# Local Imports
# Testing Imports
from ..conftest import BaseTestCase


class TestSensorUtils(BaseTestCase):
    """Test cases for validating the `physics.sensor_utils` package."""

    visual_cross_section = 25.0
    mass = 100
    reflectivity = 0.21
    solar_phase_angle = 0.5
    norm_boresight = 6371
    sun_position = array([1.47199372e08, 2.35328247e07, 1.02011844e07])
    rso_position = array([-6218.88151713, -4625.88230867, 802.87401975])
    sensor_position = array([4221.25454032, -3223.82650314, 3521.91123676])

    def testApparentVisualMagnitude(self):
        """Test apparentVisualMagnitude()."""
        apparent_vismag = apparentVisualMagnitude(
            self.visual_cross_section,
            self.reflectivity,
            lambertianPhaseFunction(self.solar_phase_angle),
            self.norm_boresight,
        )
        assert apparent_vismag == -7.7103627546277025

    def testCalculateIncidentSolarFlux(self):
        """Test calculateIncidentSolarFlux()."""
        flux = calculateIncidentSolarFlux(
            self.visual_cross_section, self.rso_position, self.sun_position
        )
        assert flux == 0.0

    def testCalculatePhaseAngle(self):
        """Test calculatePhaseAngle()."""
        phase = calculatePhaseAngle(self.sun_position, self.rso_position, self.sensor_position)
        assert phase == 0.1859393122433178

    def testCalculateSunVizFraction(self):
        """Test calculateSunVizFraction()."""
        fraction = calculateSunVizFraction(self.rso_position, self.sun_position)
        assert fraction == 0.0

    def testLambertianPhaseFunction(self):
        """Test lambertianPhaseFunction()."""
        phase = lambertianPhaseFunction(self.solar_phase_angle)
        assert phase == 0.18897354431642885
