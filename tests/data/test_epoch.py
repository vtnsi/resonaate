from __future__ import annotations

# RESONAATE Imports
from resonaate.data.epoch import Epoch


class TestEpochTable:
    """Test class for :class:`.Epoch` database table class."""

    def testInit(self):
        """Test the init of Epoch database table."""
        _ = Epoch()

    def testInitKwargs(self):
        """Test initializing the kewards of the table."""
        _ = Epoch(
            julian_date=2458207.010416667,
            timestampISO="2019-01-01T00:01:00.000Z",
        )

    def testReprAndDict(self):
        """Test printing DB table object & making into dict."""
        epoch = Epoch(
            julian_date=2458207.010416667,
            timestampISO="2019-01-01T00:01:00.000Z",
        )
        print(epoch)
        epoch.makeDictionary()

    def testEquality(self):
        """Test equals and not equals operators."""
        epoch1 = Epoch(
            julian_date=2458207.010416667,
            timestampISO="2019-01-01T00:01:00.000Z",
        )

        epoch2 = Epoch(
            julian_date=2458207.010416667,
            timestampISO="2019-01-01T00:01:00.000Z",
        )

        epoch3 = Epoch(
            julian_date=2458207.010416667,
            timestampISO="2019-01-01T00:01:00.000Z",
        )
        epoch3.julian_date += 1

        # Test equality and inequality
        assert epoch1 == epoch2
        assert epoch1 != epoch3
