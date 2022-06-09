# pylint: disable=attribute-defined-outside-init, no-self-use
# Standard Library Imports
# Third Party Imports
# RESONAATE Imports
try:
    from resonaate.physics.transforms.nutation import get1980NutationSeries
except ImportError as error:
    raise Exception(
        f"Please ensure you have appropriate packages installed:\n {error}"
    ) from error
# Testing Imports
from ..conftest import BaseTestCase


class TestNutationModel(BaseTestCase):
    """Test cases for validating the `physics.transformas` package."""

    def testNutation(self):
        """Test loading nutation files."""
        r_c, i_c = get1980NutationSeries()
        assert r_c.shape == (106, 4)
        assert i_c.shape == (106, 5)
