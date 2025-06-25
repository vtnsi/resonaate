from __future__ import annotations

# Standard Library Imports
import datetime
import os
from dataclasses import asdict

# Third Party Imports
import pytest

# RESONAATE Imports
from resonaate.physics.transforms.eops import (
    EarthOrientationParameter,
    MissingEOP,
    getEarthOrientationParameters,
)

# Local Imports
from .. import FIXTURE_DATA_DIR


@pytest.fixture(name="eop_data")
def fixtureEOPData() -> dict:
    """Create EOP data for testing."""
    return {
        "date": datetime.date(2018, 1, 1),
        "x_p": 0.059224,
        "y_p": 0.247646,
        "delta_ut1": 0.2163584,
        "length_of_day": 0.0008241,
        "d_delta_psi": -0.105116,
        "d_delta_eps": -0.008107,
        "delta_atomic_time": 37,
    }


def testInit():
    """Test initializing dataclass using positional args."""
    _ = EarthOrientationParameter(
        datetime.date(2018, 1, 1),
        0.059224,
        0.247646,
        -0.105116,
        -0.008107,
        0.2163584,
        0.0008241,
        37,
    )


def testInitKwargs(eop_data: dict):
    """Test initializing dataclass using keyword args."""
    _ = EarthOrientationParameter(**eop_data)


def testReprAndDict(eop_data: dict):
    """Test printing dataclass & making dict."""
    eop = EarthOrientationParameter(**eop_data)
    print(eop)
    asdict(eop)


def testEquality(eop_data: dict):
    """Test equals and not equals operators."""
    eop1 = EarthOrientationParameter(**eop_data)
    eop2 = EarthOrientationParameter(**eop_data)

    eop_data["x_p"] = 0.2
    eop3 = EarthOrientationParameter(**eop_data)

    assert eop1 == eop2
    assert eop1 != eop3


def testRemoteData():
    """Test loading EOP data from remote dat file."""
    q_date = datetime.date(2024, 8, 16)
    eops = getEarthOrientationParameters(
        q_date,
        loader_name="RemoteDotDatEOPLoader",
        loader_location="https://celestrak.org/SpaceData/EOP-Last5Years.txt",
    )

    assert isinstance(eops, EarthOrientationParameter)
    assert isinstance(eops.date, datetime.date)
    assert eops.date == q_date


@pytest.mark.datafiles(FIXTURE_DATA_DIR)
def testCustomEOPFile(datafiles: str):
    """Test EOP reading from custom file."""
    eop_file = os.path.join(datafiles, "dat/eops.dat")
    eops = getEarthOrientationParameters(
        datetime.date(2015, 9, 30),
        loader_name="LocalDotDatEOPLoader",
        loader_location=eop_file,
    )

    # Assert that we get the right values from the default EOP data
    assert isinstance(eops, EarthOrientationParameter)
    assert isinstance(eops.date, datetime.date)
    assert eops.delta_atomic_time == 36
    assert eops.length_of_day == 0.0019025
    assert eops.delta_ut1 == 0.2311442


def testDefaultEOPFile():
    """Test EOP reading from default file."""
    eops = getEarthOrientationParameters(datetime.date(2018, 3, 15))

    # Assert that we get the right values from the default EOP data
    assert isinstance(eops, EarthOrientationParameter)
    assert isinstance(eops.date, datetime.date)
    assert eops.delta_atomic_time == 37
    assert eops.length_of_day == 0.0009668
    assert eops.delta_ut1 == 0.1532194


def testInvalidDate():
    """Test catching bad datetime.date objects."""
    # valid date, but before our standard range of EOPs
    eop_date = datetime.date(1990, 1, 24)
    with pytest.raises(MissingEOP):
        getEarthOrientationParameters(eop_date)

    # valid date, but after range of EOPs
    eop_date = datetime.date(2050, 1, 24)
    with pytest.raises(MissingEOP):
        getEarthOrientationParameters(eop_date)


def testInvalidLoader():
    """Test catching an invalid loader name."""
    loader_name: str = "MadeUpDotDatLoader"  # Invalid loader name
    valid_date: datetime.date = datetime.date(2021, 4, 20)  # Valid date
    with pytest.raises(ValueError):  # noqa: PT011
        getEarthOrientationParameters(valid_date, loader_name=loader_name)
