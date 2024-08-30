#!/usr/bin/python

from __future__ import annotations

# Third Party Imports
import pytest

# RESONAATE Imports
from resonaate.physics.orbits.tle import InitStateLoader


@pytest.fixture(name="test_tle")
def testTLE() -> str:
    """Generates the test TLE string."""
    return """ISS (ZARYA)\n1 25544U 98067A   08264.51782528 -.00002182  00000-0 -11606-4 0  2927\n2 25544  51.6416 247.4627 0006703 130.5360 325.0288 15.72125391563537"""  # Generic test TLE


def testTLELoad(test_tle: str) -> None:
    """Tests if InitStateLoader properly loads the tle."""
    InitStateLoader(test_tle)


def testInvalidTLELength(test_tle: str) -> None:
    """Sends a TLE of invalid length to the TLE loader. Should raise an assertion errror."""
    busted_tle = test_tle + "\nI AM BROKEN\nTHIS SHOULD BREAK"
    with pytest.raises(AssertionError):
        InitStateLoader(busted_tle)


def testName(test_tle: str) -> None:
    """Tests the parsin of the satellite's name."""
    loader = InitStateLoader(test_tle)
    assert loader.name == "ISS (ZARYA)"


def testLoadNoName(test_tle: str) -> None:
    """Tests to see if the InitStateLoader.name property returns ``None`` if no optional first line is given."""
    # Get rid of the first optional / name line in the test tle.
    lines: list[str] = test_tle.split("\n")
    no_name = f"{lines[1]}\n{lines[2]}"
    loader = InitStateLoader(no_name)
    assert loader.name is None


def testCatalogNumber(test_tle: str) -> None:
    """Tests and ensures that the catalog number is being loaded correctly."""
    loader = InitStateLoader(test_tle)
    assert type(loader.catalogNumber) is int
    assert loader.catalogNumber == 25544


def testLaunchYear(test_tle: str) -> None:
    """Tests and ensures the launch year is properly parsed."""
    loader = InitStateLoader(test_tle)
    assert type(loader.launchYear) is int
    assert loader.launchYear == 98


def testLaunchNumber(test_tle: str) -> None:
    """Tests and ensures the launch number is properly parsed."""
    loader = InitStateLoader(test_tle)
    assert type(loader.launchNumber) is int
    assert loader.launchNumber == 67
