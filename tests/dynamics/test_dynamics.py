# Standard Library Imports
# Third Party Imports
from numpy import asarray
from scipy.linalg import norm

try:
    # RESONAATE Imports
    from resonaate.physics.bodies import Earth
except ImportError as error:
    raise Exception(f"Please ensure you have appropriate packages installed:\n {error}") from error
# Local Imports
# Testing Imports
from ..conftest import BaseTestCase


class TestDynamics(BaseTestCase):
    """Test class for dynamics class."""

    def testEarthCrash(self):
        """Test to make sure an assert is raised if a RSO crashes into the Earth."""
        stable_orbit = asarray([41574.6, 6681.53, 0, -0.485045, 3.03858, 0])
        assert norm(stable_orbit[:3]) > Earth.radius

        crash_orbit = asarray([6088.234341, 50.29079, 8.763258, -1.999674, 6.626409, 3.597847])
        assert norm(crash_orbit[:3]) < Earth.radius
