from __future__ import annotations

# Standard Library Imports
from copy import deepcopy

# Third Party Imports
from sqlalchemy.orm import Query

# RESONAATE Imports
from resonaate.data.observation import Observation
from resonaate.sensors import OPTICAL_LABEL


class TestObservationTable:
    """Test class for :class:`.Observation` database table class."""

    sez = [
        -4957.659229144096,
        7894.2462525123365,
        3193.9292760074436,
        1.7500003208790118,
        3.931727930569842,
        -2.338646528282177,
    ]

    azimuth_rad = 1.010036549841
    elevation_rad = 0.33006189181
    position_lat_rad = 0.44393147656176574
    position_lon_rad = 1.124890532
    position_altitude_km = 0.6253
    sensor_type = OPTICAL_LABEL

    def testInit(self):
        """Test the init of Observation database table."""
        _ = Observation()

    def testInitKwargs(self, epoch, target_agent, sensor_agent):
        """Test initializing the keywords of the table."""
        _ = Observation(
            epoch=epoch,
            sensor=sensor_agent,
            target=target_agent,
            sensor_type=self.sensor_type,
            azimuth_rad=self.azimuth_rad,
            elevation_rad=self.elevation_rad,
            position_lat_rad=self.position_lat_rad,
            position_lon_rad=self.position_lon_rad,
            position_altitude_km=self.position_altitude_km,
        )

    def testfromSEZVector(self, epoch, target_agent, sensor_agent):
        """Test initializing the keywords of the table."""
        _ = Observation(
            epoch=epoch,
            sensor=sensor_agent,
            target=target_agent,
            sensor_type=self.sensor_type,
            azimuth_rad=self.azimuth_rad,
            elevation_rad=self.elevation_rad,
            position_lat_rad=self.position_lat_rad,
            position_lon_rad=self.position_lon_rad,
            position_altitude_km=self.position_altitude_km,
        )

    def testReprAndDict(self, epoch, target_agent, sensor_agent):
        """Test printing DB table object & making into dict."""
        obs = Observation(
            epoch=epoch,
            sensor=sensor_agent,
            target=target_agent,
            sensor_type=self.sensor_type,
            azimuth_rad=self.azimuth_rad,
            elevation_rad=self.elevation_rad,
            position_lat_rad=self.position_lat_rad,
            position_lon_rad=self.position_lon_rad,
            position_altitude_km=self.position_altitude_km,
        )
        print(obs)
        obs.makeDictionary()

    def testEquality(self, epoch, target_agent, sensor_agent):
        """Test equals and not equals operators."""
        obs1 = Observation(
            epoch=epoch,
            sensor=sensor_agent,
            target=target_agent,
            sensor_type=self.sensor_type,
            azimuth_rad=self.azimuth_rad,
            elevation_rad=self.elevation_rad,
            position_lat_rad=self.position_lat_rad,
            position_lon_rad=self.position_lon_rad,
            position_altitude_km=self.position_altitude_km,
        )

        obs2 = Observation(
            epoch=epoch,
            sensor=sensor_agent,
            target=target_agent,
            sensor_type=self.sensor_type,
            azimuth_rad=self.azimuth_rad,
            elevation_rad=self.elevation_rad,
            position_lat_rad=self.position_lat_rad,
            position_lon_rad=self.position_lon_rad,
            position_altitude_km=self.position_altitude_km,
        )

        obs3 = Observation(
            epoch=epoch,
            sensor=sensor_agent,
            target=target_agent,
            sensor_type=self.sensor_type,
            azimuth_rad=self.azimuth_rad,
            elevation_rad=self.elevation_rad,
            position_lat_rad=self.position_lat_rad,
            position_lon_rad=self.position_lon_rad,
            position_altitude_km=self.position_altitude_km,
        )
        obs3.range_km = 500

        # Test equality and inequality
        assert obs1 == obs2
        assert obs1 != obs3

    def testMeasurementProperty(self, epoch, target_agent, sensor_agent):
        """Test sez property."""
        obs = Observation(
            epoch=epoch,
            sensor=sensor_agent,
            target=target_agent,
            sensor_type="AdvRadar",
            azimuth_rad=1.010036549841,
            elevation_rad=0.33006189181,
            range_km=1500.0,
            range_rate_km_p_sec=0.10,
            position_lat_rad=0.44393147656176574,
            position_lon_rad=1.124890532,
            position_altitude_km=0.6253,
        )
        assert isinstance(obs.measurements, list)
        assert len(obs.measurements) == 4

    def testInsertWithRelationship(self, database, epoch, target_agent, sensor_agent):
        """Test inserting observation with related objects."""
        obs = Observation(
            epoch=epoch,
            sensor=sensor_agent,
            target=target_agent,
            sensor_type=self.sensor_type,
            azimuth_rad=self.azimuth_rad,
            elevation_rad=self.elevation_rad,
            position_lat_rad=self.position_lat_rad,
            position_lon_rad=self.position_lon_rad,
            position_altitude_km=self.position_altitude_km,
        )

        # Test insert of object
        database.insertData(obs)

    def testInsertWithForeignKeys(self, database, epoch, target_agent, sensor_agent):
        """Test inserting observation with only foreign keys."""
        obs = Observation(
            julian_date=epoch.julian_date,
            sensor_id=sensor_agent.unique_id,
            target_id=target_agent.unique_id,
            sensor_type=self.sensor_type,
            azimuth_rad=self.azimuth_rad,
            elevation_rad=self.elevation_rad,
            position_lat_rad=self.position_lat_rad,
            position_lon_rad=self.position_lon_rad,
            position_altitude_km=self.position_altitude_km,
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
        obs = Observation(
            epoch=epoch,
            sensor=sensor_agent,
            target=target_agent,
            sensor_type=self.sensor_type,
            azimuth_rad=self.azimuth_rad,
            elevation_rad=self.elevation_rad,
            position_lat_rad=self.position_lat_rad,
            position_lon_rad=self.position_lon_rad,
            position_altitude_km=self.position_altitude_km,
        )
        database.insertData(obs)

        new_obs = database.getData(Query(Observation), multi=False)
        # Test lazy-loading behavior for relationship() attributes
        assert new_obs.epoch.julian_date == julian_date
        assert new_obs.target.unique_id == target_id
        assert new_obs.sensor.unique_id == sensor_id

    def testManyToOneQuery(self, database, epoch, target_agent, sensor_agent):
        """Test many to one relationship queries."""
        epoch_copy = deepcopy(epoch)
        target_copy = deepcopy(target_agent)
        sensor_copy = deepcopy(sensor_agent)

        obs = Observation(
            epoch=epoch,
            sensor=sensor_agent,
            target=target_agent,
            sensor_type=self.sensor_type,
            azimuth_rad=self.azimuth_rad,
            elevation_rad=self.elevation_rad,
            position_lat_rad=self.position_lat_rad,
            position_lon_rad=self.position_lon_rad,
            position_altitude_km=self.position_altitude_km,
        )
        database.insertData(obs)

        # Test querying by Target
        query = Query(Observation).filter(Observation.target == target_copy)
        new_obs = database.getData(query, multi=False)
        assert new_obs.target == target_copy

        # Test querying by Sensor
        query = Query(Observation).filter(Observation.sensor == sensor_copy)
        new_obs = database.getData(query, multi=False)
        assert new_obs.sensor == sensor_copy

        # Test querying by epoch
        query = Query(Observation).filter(Observation.epoch == epoch_copy)
        new_obs = database.getData(query, multi=False)
        assert new_obs.epoch == epoch_copy
