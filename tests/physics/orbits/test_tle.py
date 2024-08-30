#!/usr/bin/python

from __future__ import annotations

# Third Party Imports
import pytest

# RESONAATE Imports
from resonaate.physics.orbits.tle import InitStateLoader


@pytest.fixture(name="test_tle")
def testTLE() -> str:
    """Generates the test TLE string."""
    return """ISS (ZARYA)
\n1 25544U 98067A   08264.51782528 -.00002182  00000-0 -11606-4 0  2927
\n2 25544  51.6416 247.4627 0006703 130.5360 325.0288 15.72125391563537"""  # Generic test TLE


def testTLELoad(test_tle: str) -> None:
    """Tests if InitStateLoader properly loads the tle."""
    InitStateLoader(test_tle)


def testInvalidTLELength(test_tle) -> None:
    """Sends a TLE of invalid length to the TLE loader. Should raise an assertion errror."""
    busted_tle = test_tle + "\nI AM BROKEN\nTHIS SHOULD BREAK"
    with pytest.raises(AssertionError):
        InitStateLoader(busted_tle)
