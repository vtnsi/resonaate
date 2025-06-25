from __future__ import annotations

# Standard Library Imports
from math import hypot

# Third Party Imports
import pytest
from numpy import isclose

# RESONAATE Imports
from resonaate.physics.orbits.tle import TLELoader
from resonaate.physics.orbits.utils import getMeanMotion, getSemiMajorAxis
from resonaate.physics.time.stardate import JulianDate


@pytest.fixture(name="test_tle")
def createTestTLE() -> str:
    """Returns the test TLE string."""
    return """ISS (ZARYA)\n1 25544U 98067A   20264.51782528 -.00002182  00000-0 -11606-4 0  2927\n2 25544  51.6416 247.4627 0006703 130.5360 325.0288 15.72125391563537"""  # Generic test TLE


@pytest.fixture(name="test_epoch")
def createTestEpoch() -> JulianDate:
    """Returns the test epoch. Note that this is hard coded and needs to be changed if the above test TLE changes."""
    date: float = 2458849.5 + 264.51782528
    return JulianDate(date)


def testTLELoad(test_tle: str) -> None:
    """Tests if TLELoader properly loads the tle."""
    TLELoader(test_tle)


def testInvalidTLELength(test_tle: str) -> None:
    """Sends a TLE of invalid length to the TLE loader. Should raise an assertion errror."""
    busted_tle = test_tle + "\nI AM BROKEN\nTHIS SHOULD BREAK"
    with pytest.raises(AssertionError):
        TLELoader(busted_tle)


def testName(test_tle: str) -> None:
    """Tests the parsin of the satellite's name."""
    loader = TLELoader(test_tle)
    assert loader.name == "ISS (ZARYA)"


def testLoadNoName(test_tle: str) -> None:
    """Tests to see if the TLELoader.name property returns ``None`` if no optional first line is given."""
    # Get rid of the first optional / name line in the test tle.
    lines: list[str] = test_tle.split("\n")
    no_name = f"{lines[1]}\n{lines[2]}"
    loader = TLELoader(no_name)
    assert loader.name is None


def testcatalog_number(test_tle: str) -> None:
    """Tests and ensures that the catalog number is being loaded correctly."""
    loader = TLELoader(test_tle)
    assert type(loader.catalog_number) is int
    assert loader.catalog_number == 25544


def testlaunch_year(test_tle: str) -> None:
    """Tests and ensures the launch year is properly parsed."""
    loader = TLELoader(test_tle)
    assert type(loader.launch_year) is int
    assert loader.launch_year == 98


def testlaunch_number(test_tle: str) -> None:
    """Tests and ensures the launch number is properly parsed."""
    loader = TLELoader(test_tle)
    assert type(loader.launch_number) is int
    assert loader.launch_number == 67


def testEpoch(test_tle: str, test_epoch: JulianDate) -> None:
    """Tests parsing of the Epoch."""
    loader = TLELoader(test_tle)
    assert (
        loader.epoch == test_epoch
    ), f"Test Epoch = {float(test_epoch)}, Parsed Epoch = {float(loader.epoch)}"


def testInclination(test_tle: str) -> None:
    """Tests parsing the inclination."""
    loader = TLELoader(test_tle)
    assert loader.inclination == 51.6416


def testRaan(test_tle: str) -> None:
    """Tests parsing of the right ascension of the ascending node."""
    loader = TLELoader(test_tle)
    assert loader.right_ascension == 247.4627


def testEccentricity(test_tle: str) -> None:
    """Tests the parsing of the eccentricity."""
    loader = TLELoader(test_tle)
    assert loader.eccentricity == 0.0006703


def testargument_of_periapsis(test_tle: str) -> None:
    """Tests parsing of the argument of periapsis."""
    loader = TLELoader(test_tle)
    assert loader.argument_of_periapsis == 130.5360


def testMeanAnomaly(test_tle: str) -> None:
    """Tests parsing of the mean anomaly."""
    loader = TLELoader(test_tle)
    assert loader.mean_anomaly == 325.0288


def testmean_motion(test_tle: str) -> None:
    """Tests parsing of the mean motion into radians per second."""
    loader = TLELoader(test_tle)
    assert loader.mean_motion == 0.0011432818469647179


def testsemi_major_axis(test_tle: str) -> None:
    """Tests the parsing and computation of the semi major axis."""
    loader = TLELoader(test_tle)
    sma = loader.semi_major_axis
    assert isclose(loader.mean_motion, getMeanMotion(sma))


def testSGP4Propagation(test_tle: str) -> None:
    """Tests the propagation of truth orbital elements."""
    loader = TLELoader(test_tle)

    # TODO: Tests these properties against actual data. Right now all that's happening is making sure the code executes without errors.
    eci = loader.init_eci_config
    v = hypot(eci.velocity[0], eci.velocity[1], eci.velocity[2])
    r = hypot(eci.position[0], eci.position[1], eci.position[2])

    coe = loader.init_coe_config

    # Compute the SMA from the eci elements and make sure it lines up with what's in the COE config.
    sma = getSemiMajorAxis(r, v)

    assert isclose(sma, coe.semi_major_axis)
