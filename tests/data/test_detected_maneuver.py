from __future__ import annotations

# Standard Library Imports
from copy import deepcopy

# Third Party Imports
from sqlalchemy.orm import Query

# RESONAATE Imports
from resonaate.data.detected_maneuver import DetectedManeuver


class TestDetectedManeuver:
    """Test class for :class:`.DetectedManeuver` database table class."""

    def testInit(self):
        """Test the init of DetectedManeuver database table."""
        _ = DetectedManeuver()

    def testInitKwargs(self):
        """Test initializing the kewards of the table."""
        _ = DetectedManeuver(
            julian_date=2458207.010416667,
            sensor_ids="1,2,3",
            target_id=20000,
            nis=200.0,
            method="StandardNis",
            metric=200.0,
            threshold=0.05,
        )

    def testReprAndDict(self):
        """Test printing DB table object & making into dict."""
        det = DetectedManeuver(
            julian_date=2458207.010416667,
            sensor_ids="1,2,3",
            target_id=20000,
            nis=200.0,
            method="StandardNis",
            metric=200.0,
            threshold=0.05,
        )
        print(det)
        det.makeDictionary()
        sensor_list = det.sensor_list
        assert isinstance(sensor_list, list)
        for sensor in sensor_list:
            assert isinstance(sensor, int)

    def testEquality(self):
        """Test equals and not equals operators."""
        det1 = DetectedManeuver(
            julian_date=2458207.010416667,
            sensor_ids="1,2,3",
            target_id=20000,
            nis=200.0,
            method="StandardNis",
            metric=200.0,
            threshold=0.05,
        )

        det2 = DetectedManeuver(
            julian_date=2458207.010416667,
            sensor_ids="1,2,3",
            target_id=20000,
            nis=200.0,
            method="StandardNis",
            metric=200.0,
            threshold=0.05,
        )

        det3 = DetectedManeuver(
            julian_date=2458207.010416667,
            sensor_ids="1,2,3",
            target_id=20000,
            nis=200.0,
            method="StandardNis",
            metric=200.0,
            threshold=0.05,
        )
        det3.julian_date += 1

        # Test equality and inequality
        assert det1 == det2
        assert det1 != det3

    def testInsertWithRelationship(self, database, epoch, target_agent):
        """Test inserting ephemeris with related objects."""
        det = DetectedManeuver(
            epoch=epoch,
            target=target_agent,
            sensor_ids="1,2,3",
            nis=200.0,
            method="FadingMemoryNis",
            metric=120.0,
            threshold=0.05,
        )

        # Test insert of object
        database.insertData(det)

    def testInsertWithForeignKeys(self, database, epoch, target_agent):
        """Test inserting ephemeris with only foreign keys."""
        det = DetectedManeuver(
            julian_date=epoch.julian_date,
            target_id=target_agent.unique_id,
            sensor_ids="1,2,3",
            nis=200.0,
            method="FadingMemoryNis",
            metric=120.0,
            threshold=0.05,
        )
        # Pre-insert required objects
        database.insertData(epoch)
        database.insertData(target_agent)

        # Test insert of object via FK
        database.insertData(det)

    def testManyToOneLazyLoading(self, database, epoch, target_agent):
        """Test many to one lazy-loading attributes."""
        julian_date = epoch.julian_date
        agent_id = target_agent.unique_id
        det = DetectedManeuver(
            epoch=epoch,
            target=target_agent,
            sensor_ids="1,2,3",
            nis=200.0,
            method="FadingMemoryNis",
            metric=120.0,
            threshold=0.05,
        )
        database.insertData(det)

        new_ephem = database.getData(Query(DetectedManeuver), multi=False)
        # Test lazy-loading behavior for relationship() attributes
        assert new_ephem.target.unique_id == agent_id
        assert new_ephem.epoch.julian_date == julian_date

    def testManyToOneQuery(self, database, epoch, target_agent):
        """Test many to one relationship queries."""
        epoch_copy = deepcopy(epoch)
        agent_copy = deepcopy(target_agent)

        det = DetectedManeuver(
            epoch=epoch,
            target=target_agent,
            sensor_ids="1,2,3",
            nis=200.0,
            method="FadingMemoryNis",
            metric=120.0,
            threshold=0.05,
        )
        database.insertData(det)

        # Test querying by AgentModel
        query = Query(DetectedManeuver).filter(DetectedManeuver.target == agent_copy)
        new_det = database.getData(query, multi=False)
        assert new_det.target == agent_copy

        # Test querying by Epoch
        query = Query(DetectedManeuver).filter(DetectedManeuver.epoch == epoch_copy)
        new_det = database.getData(query, multi=False)
        assert new_det.epoch == epoch_copy
