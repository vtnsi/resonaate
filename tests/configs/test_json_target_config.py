# pylint: disable=attribute-defined-outside-init, import-outside-toplevel, reimported
# Standard Library Imports
from json import load
from os import listdir

# Third Party Imports
from numpy import array
from scipy.linalg import norm

# RESONAATE Library Imports
try:
    # RESONAATE Imports
    from resonaate.physics.bodies import Earth
except ImportError as error:
    raise Exception(f"Please ensure you have appropriate packages installed:\n {error}") from error
# Local Imports
# Testing Imports
from ..conftest import BaseTestCase


class TestJSONTargetConfig(BaseTestCase):
    """Class to test configs/json/targets/."""

    def testStationKeepingAssignment(self):
        """Test that every target has proper station keeping based on orbital regime."""
        for target_sets in listdir("configs/json/targets"):
            with open(
                f"configs/json/targets/{str(target_sets)}", "r", encoding="utf-8"
            ) as target_set:
                targets = load(target_set)

            for target in targets:
                if "routines" in target["station_keeping"]:
                    pos = array(target["init_eci"][:3])
                    vel = array(target["init_eci"][3:])
                    energy = (norm(vel) ** 2 / 2) - (Earth.mu / norm(pos))
                    semimajor_axis = -Earth.mu / (2 * energy)

                    if target["station_keeping"]["routines"] == []:
                        continue

                    # Test assertions
                    if semimajor_axis > 40000:
                        assert target["station_keeping"]["routines"] == ["GEO EW", "GEO NS"]
                    elif semimajor_axis < 10000:
                        assert target["station_keeping"]["routines"] == ["LEO"]
