from __future__ import annotations

# Standard Library Imports
from copy import deepcopy

# Third Party Imports
from sqlalchemy.orm import Query

# RESONAATE Imports
from resonaate.data.missed_observation import MissedObservation
from resonaate.sensors import OPTICAL_LABEL


class TestMissedObservationTable:
    """Test class for :class:`.MissedObservation` database table class."""

    _type = OPTICAL_LABEL

    sez = [
        -4957.659229144096,
        7894.2462525123365,
        3193.9292760074436,
    ]

    lla = [
        0.44393147656176574,
        1.124890532,
        0.6253,
    ]

    def testInit(self):
        """Test the init of MissedObservation database table."""
        _ = MissedObservation()

    def testInitKwargs(self, epoch, target_agent, sensor_agent):
        """Test initializing the keywords of the table."""
        _ = MissedObservation(
            epoch=epoch,
            sensor=sensor_agent,
            target=target_agent,
            sensor_type=self._type,
            position_lat_rad=self.lla[0],
            position_lon_rad=self.lla[1],
            position_altitude_km=self.lla[2],
            reason=MissedObservation.Explanation.VISIBLE.value,
        )

    def testReprAndDict(self, epoch, target_agent, sensor_agent):
        """Test printing DB table object & making into dict."""
        missed_ob = MissedObservation(
            epoch=epoch,
            sensor=sensor_agent,
            target=target_agent,
            sensor_type=self._type,
            position_lat_rad=self.lla[0],
            position_lon_rad=self.lla[1],
            position_altitude_km=self.lla[2],
            reason=MissedObservation.Explanation.MINIMUM_RANGE.value,
        )
        print(missed_ob)
        missed_ob.makeDictionary()

    def testEquality(self, epoch, target_agent, sensor_agent):
        """Test equals and not equals operators."""
        obs1 = MissedObservation(
            epoch=epoch,
            sensor=sensor_agent,
            target=target_agent,
            sensor_type=self._type,
            position_lat_rad=self.lla[0],
            position_lon_rad=self.lla[1],
            position_altitude_km=self.lla[2],
            reason=MissedObservation.Explanation.MAXIMUM_RANGE.value,
        )

        obs2 = MissedObservation(
            epoch=epoch,
            sensor=sensor_agent,
            target=target_agent,
            sensor_type=self._type,
            position_lat_rad=self.lla[0],
            position_lon_rad=self.lla[1],
            position_altitude_km=self.lla[2],
            reason=MissedObservation.Explanation.MAXIMUM_RANGE.value,
        )

        obs3 = MissedObservation(
            epoch=epoch,
            sensor=sensor_agent,
            target=target_agent,
            sensor_type=self._type,
            position_lat_rad=self.lla[0],
            position_lon_rad=self.lla[1],
            position_altitude_km=self.lla[2],
            reason=MissedObservation.Explanation.MAXIMUM_RANGE.value,
        )
        obs3.position_altitude_km = 500

        # Test equality and inequality
        assert obs1 == obs2
        assert obs1 != obs3

    def testLLAProperty(self, epoch, target_agent, sensor_agent):
        """Test lla property."""
        obs = MissedObservation(
            epoch=epoch,
            sensor=sensor_agent,
            target=target_agent,
            sensor_type=self._type,
            position_lat_rad=self.lla[0],
            position_lon_rad=self.lla[1],
            position_altitude_km=self.lla[2],
            reason=MissedObservation.Explanation.LINE_OF_SIGHT.value,
        )
        assert isinstance(obs.lla, list)
        assert len(obs.lla) == 3

    def testInsertWithRelationship(self, database, epoch, target_agent, sensor_agent):
        """Test inserting MissedObservation with related objects."""
        obs = MissedObservation(
            epoch=epoch,
            sensor=sensor_agent,
            target=target_agent,
            sensor_type=self._type,
            position_lat_rad=self.lla[0],
            position_lon_rad=self.lla[1],
            position_altitude_km=self.lla[2],
            reason=MissedObservation.Explanation.AZIMUTH_MASK.value,
        )

        # Test insert of object
        database.insertData(obs)

    def testInsertWithForeignKeys(self, database, epoch, target_agent, sensor_agent):
        """Test inserting missed observation with only foreign keys."""
        obs = MissedObservation(
            epoch=epoch,
            sensor=sensor_agent,
            target=target_agent,
            sensor_type=self._type,
            position_lat_rad=self.lla[0],
            position_lon_rad=self.lla[1],
            position_altitude_km=self.lla[2],
            reason=MissedObservation.Explanation.ELEVATION_MASK.value,
        )
        # Pre-insert required objects
        database.insertData(epoch)
        database.insertData(target_agent)
        database.insertData(sensor_agent)

        # Test insert of object via FK
        database.insertData(obs)

    def testManyToOneLazyLoading(self, database, epoch, target_agent, sensor_agent):
        """Test many to one lazy-loading attributes."""
        julian_date = epoch.julian_date
        target_id = target_agent.unique_id
        sensor_id = sensor_agent.unique_id
        obs = MissedObservation(
            epoch=epoch,
            sensor=sensor_agent,
            target=target_agent,
            sensor_type=self._type,
            position_lat_rad=self.lla[0],
            position_lon_rad=self.lla[1],
            position_altitude_km=self.lla[2],
            reason=MissedObservation.Explanation.VIZ_MAG.value,
        )
        database.insertData(obs)

        new_obs = database.getData(Query(MissedObservation), multi=False)
        # Test lazy-loading behavior for relationship() attributes
        assert new_obs.epoch.julian_date == julian_date
        assert new_obs.target.unique_id == target_id
        assert new_obs.sensor.unique_id == sensor_id

    def testManyToOneQuery(self, database, epoch, target_agent, sensor_agent):
        """Test many to one relationship queries."""
        epoch_copy = deepcopy(epoch)
        target_copy = deepcopy(target_agent)
        sensor_copy = deepcopy(sensor_agent)

        obs = MissedObservation(
            epoch=epoch,
            sensor=sensor_agent,
            target=target_agent,
            sensor_type=self._type,
            position_lat_rad=self.lla[0],
            position_lon_rad=self.lla[1],
            position_altitude_km=self.lla[2],
            reason=MissedObservation.Explanation.SOLAR_FLUX.value,
        )
        database.insertData(obs)

        # Test querying by Target
        query = Query(MissedObservation).filter(MissedObservation.target == target_copy)
        new_obs = database.getData(query, multi=False)
        assert new_obs.target == target_copy

        # Test querying by Sensor
        query = Query(MissedObservation).filter(MissedObservation.sensor == sensor_copy)
        new_obs = database.getData(query, multi=False)
        assert new_obs.sensor == sensor_copy

        # Test querying by epoch
        query = Query(MissedObservation).filter(MissedObservation.epoch == epoch_copy)
        new_obs = database.getData(query, multi=False)
        assert new_obs.epoch == epoch_copy
