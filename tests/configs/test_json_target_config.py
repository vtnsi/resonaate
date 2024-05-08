from __future__ import annotations

# Standard Library Imports
from json import load
from os import listdir

# Third Party Imports
from numpy import array
from scipy.linalg import norm

# RESONAATE Imports
from resonaate.physics.bodies import Earth


def testStationKeepingAssignment():
    """Test that every target has proper station keeping based on orbital regime."""
    for target_sets in listdir("configs/json/targets"):
        with open(f"configs/json/targets/{target_sets!s}", encoding="utf-8") as target_set:
            targets = load(target_set)

        for target in targets:
            if "station_keeping" not in target["platform"]:
                continue
            station_keeping = target["platform"]["station_keeping"]

            if "routines" not in station_keeping:
                continue

            state = target["state"]
            if state["type"] != "eci":
                continue

            pos = array(state["position"])
            vel = array(state["velocity"])
            energy = (norm(vel) ** 2 / 2) - (Earth.mu / norm(pos))
            semimajor_axis = -Earth.mu / (2 * energy)

            if station_keeping["routines"] == []:
                continue

            # Test assertions
            if semimajor_axis > 40000:
                assert station_keeping["routines"] == ["GEO EW", "GEO NS"]
            elif semimajor_axis < 10000:
                assert station_keeping["routines"] == ["LEO"]
