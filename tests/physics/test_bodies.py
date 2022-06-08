# pylint: disable=attribute-defined-outside-init, no-self-use
# Standard Library Imports
# Third Party Imports
from numpy import asarray, ndarray, allclose
import pytest
# RESONAATE Imports
try:
    from resonaate.physics.bodies import Earth
    from resonaate.physics.bodies.third_body import Moon, Sun
    from resonaate.physics.time.stardate import JulianDate
except ImportError as error:
    raise Exception(
        "Please ensure you have appropriate packages installed:\n {0}".format(error)
    ) from error
# Testing Imports
from ..conftest import BaseTestCase


class TestThirdBody(BaseTestCase):
    """Perform set of test on the Third Body module."""

    def testSun(self):
        """Perform simple set of tests on the Sun class."""
        true_position = asarray([1.19057221e+08, -80174634.82332915, -34756419.36076262])
        julian_date = JulianDate(2458527.5)
        sun_position = Sun.getPosition(julian_date)

        # Test assertions
        assert isinstance(sun_position, ndarray)
        assert sun_position.shape == (3, )
        assert allclose(true_position, sun_position, rtol=1e-8, atol=1e-12)

    def testMoon(self):
        """Perform simple set of tests on the Moon class."""
        true_position = asarray([222662.48906104, 298651.50080616, 95734.9324735])
        julian_date = JulianDate(2458527.5)
        moon_position = Moon.getPosition(julian_date)

        # Test assertions
        assert isinstance(moon_position, ndarray)
        assert moon_position.shape == (3, )
        assert allclose(true_position, moon_position, rtol=1e-8, atol=1e-12)


class TestEarth:
    """Perform set of test on the Earth module."""

    TEST_CASES = [
        # (degree, order, [truth])
        (2, 0, [-0.023402725520133, 0.178921657872794, -0.158647615812368]),
        (4, 4, [-0.025272814133158, 0.180129562607620, -0.156608150434144]),
        (16, 16, [-0.025220531457556, 0.180512517258954, -0.156448742777998]),
        (48, 48, [-0.025220876219449, 0.180513294718102, -0.156448843984580]),
    ]

    ITRF_POSITION = asarray([-1033.4793830, 7901.2952754, 6380.3565958])  # km

    @pytest.mark.parametrize("degree, order, truth", TEST_CASES)
    def testGeoPotentialFunction(self, degree, order, truth):
        """Test the non-spherical geopotential acceleration function."""
        earth = Earth("egm96.txt")
        accelerations = earth.nonSphericalGeopotential(self.ITRF_POSITION, degree, order)
        assert allclose(accelerations, asarray(truth) * 1e-5, atol=1e-10, rtol=1e-8)
