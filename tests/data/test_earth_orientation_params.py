# pylint: disable=attribute-defined-outside-init, no-self-use
# Standard Library Imports
from datetime import date
# Third Party Imports
import pytest
# RESONAATE Imports
try:
    from resonaate.data.earth_orientation_params import EarthOrientationParams, NutationParams
except ImportError as error:
    raise Exception(
        "Please ensure you have appropriate packages installed:\n {0}".format(error)
    ) from error
# Testing Imports
from ..conftest import BaseTestCase


class TestEarthOrientationTables(BaseTestCase):
    """Tests for :class:`.EarthOrientationParams` & :class:`.NutationParams` classes."""

    @pytest.fixture(scope="function", autouse=True)
    def fixtureEOPData(self):
        """Create EOP data for testing."""
        self.eop_data = [
            2018, 1, 1, 58119, 0.059224, 0.247646, 0.2163584, 0.0008241,
            -0.105116, -0.008107, 0.000094, -0.000026, 37
        ]
        self.nut_data = [
            0, 0, 0, 0, 1, -171996, -174.2, 92025, 8.9, 1
        ]

    def testInit(self):
        """Test initializing empty DB table objects."""
        _ = EarthOrientationParams()
        _ = NutationParams()

    def testInitKwargs(self):
        """Test initializing DB table objects using keyword args."""
        test_date = date(*self.eop_data[:3])
        _ = EarthOrientationParams(
            eop_date=test_date,
            x_p=self.eop_data[4],
            y_p=self.eop_data[5],
            delta_ut1=self.eop_data[6],
            length_of_day=self.eop_data[7],
            d_delta_psi=self.eop_data[8],
            d_delta_eps=self.eop_data[9],
            delta_atomic_time=self.eop_data[12],
        )
        _ = NutationParams(
            a_n1_i=self.nut_data[0],
            a_n2_i=self.nut_data[1],
            a_n3_i=self.nut_data[2],
            a_n4_i=self.nut_data[3],
            a_n5_i=self.nut_data[4],
            a_i=self.nut_data[5],
            b_i=self.nut_data[6],
            c_i=self.nut_data[7],
            d_i=self.nut_data[8],
        )
