# pylint: disable=attribute-defined-outside-init, no-self-use
# Standard Library Imports
from copy import deepcopy
# Third Party Imports
from sqlalchemy.orm import Query
# RESONAATE Imports
try:
    from resonaate.data.resonaate_database import ResonaateDatabase
    from resonaate.data.observation import Observation
except ImportError as error:
    raise Exception(
        f"Please ensure you have appropriate packages installed:\n {error}"
    ) from error
# Testing Imports
from ..conftest import BaseTestCase


class TestObservationTable(BaseTestCase):
    """Test class for :class:`.Observation` database table class."""

    sez = [
        -4957.659229144096, 7894.2462525123365, 3193.9292760074436,
        1.7500003208790118, 3.931727930569842, -2.338646528282177
    ]

    def testInit(self):
        """Test the init of Observation database table."""
        _ = Observation()

    def testInitKwargs(self, epoch, target_agent, sensor_agent):
        """Test initializing the kewards of thetable."""
        _ = Observation(
            epoch=epoch,
            sensor=sensor_agent,
            target=target_agent,
            sensor_type="Optical",
            azimuth_rad=1.010036549841,
            elevation_rad=0.33006189181,
            sez_state_s_km=-4957.659229144096,
            sez_state_e_km=7894.2462525123365,
            sez_state_z_km=3193.92927600744,
            position_lat_rad=0.44393147656176574,
            position_long_rad=1.124890532,
            position_altitude_km=0.6253
        )

    def testfromSEZVector(self, epoch, target_agent, sensor_agent):
        """Test initializing the kewards of the table."""
        _ = Observation.fromSEZVector(
            epoch=epoch,
            sensor=sensor_agent,
            target=target_agent,
            sensor_type="Optical",
            azimuth_rad=1.010036549841,
            elevation_rad=0.33006189181,
            sez=self.sez,
            sensor_position=[0.44393147656176574, 1.124890532, 0.6253]
        )

    def testReprAndDict(self, epoch, target_agent, sensor_agent):
        """Test printing DB table object & making into dict."""
        obs = Observation.fromSEZVector(
            epoch=epoch,
            sensor=sensor_agent,
            target=target_agent,
            sensor_type="Optical",
            azimuth_rad=1.010036549841,
            elevation_rad=0.33006189181,
            sez=self.sez,
            sensor_position=[0.44393147656176574, 1.124890532, 0.6253]
        )
        print(obs)
        obs.makeDictionary()

    def testEquality(self, epoch, target_agent, sensor_agent):
        """Test equals and not equals operators."""
        obs1 = Observation.fromSEZVector(
            epoch=epoch,
            sensor=sensor_agent,
            target=target_agent,
            sensor_type="Optical",
            azimuth_rad=1.010036549841,
            elevation_rad=0.33006189181,
            sez=self.sez,
            sensor_position=[0.44393147656176574, 1.124890532, 0.6253]
        )

        obs2 = Observation.fromSEZVector(
            epoch=epoch,
            sensor=sensor_agent,
            target=target_agent,
            sensor_type="Optical",
            azimuth_rad=1.010036549841,
            elevation_rad=0.33006189181,
            sez=self.sez,
            sensor_position=[0.44393147656176574, 1.124890532, 0.6253]
        )

        obs3 = Observation.fromSEZVector(
            epoch=epoch,
            sensor=sensor_agent,
            target=target_agent,
            sensor_type="Optical",
            azimuth_rad=1.010036549841,
            elevation_rad=0.33006189181,
            sez=self.sez,
            sensor_position=[0.44393147656176574, 1.124890532, 0.6253]
        )
        obs3.range_km = 500

        # Test equality and inequality
        assert obs1 == obs2
        assert obs1 != obs3

    def testSEZProperty(self, epoch, target_agent, sensor_agent):
        """Test sez property."""
        obs = Observation.fromSEZVector(
            epoch=epoch,
            sensor=sensor_agent,
            target=target_agent,
            sensor_type="Optical",
            azimuth_rad=1.010036549841,
            elevation_rad=0.33006189181,
            sez=self.sez,
            sensor_position=[0.44393147656176574, 1.124890532, 0.6253]
        )
        assert isinstance(obs.sez, list)
        assert len(obs.sez) == 3

    def testMeasurementProperty(self, epoch, target_agent, sensor_agent):
        """Test sez property."""
        obs = Observation.fromSEZVector(
            epoch=epoch,
            sensor=sensor_agent,
            target=target_agent,
            sensor_type="AdvRadar",
            azimuth_rad=1.010036549841,
            elevation_rad=0.33006189181,
            range_km=1500.0,
            range_rate_km_p_sec=0.10,
            sez=self.sez,
            sensor_position=[0.44393147656176574, 1.124890532, 0.6253]
        )
        assert isinstance(obs.measurements, list)
        assert len(obs.measurements) == 4

    def testInsertWithRelationship(self, epoch, target_agent, sensor_agent):
        """Test inserting observation with related objects."""
        database = ResonaateDatabase.getSharedInterface()
        obs = Observation.fromSEZVector(
            epoch=epoch,
            sensor=sensor_agent,
            target=target_agent,
            sensor_type="Optical",
            azimuth_rad=1.010036549841,
            elevation_rad=0.33006189181,
            sez=self.sez,
            sensor_position=[0.44393147656176574, 1.124890532, 0.6253]
        )

        # Test insert of object
        database.insertData(obs)

        # Reset DB
        database.resetData(ResonaateDatabase.VALID_DATA_TYPES)

    def testInsertWithForeignKeys(self, epoch, target_agent, sensor_agent):
        """Test inserting observation with only foreign keys."""
        database = ResonaateDatabase.getSharedInterface()
        obs = Observation.fromSEZVector(
            julian_date=epoch.julian_date,
            sensor_id=sensor_agent.unique_id,
            target_id=target_agent.unique_id,
            sensor_type="Optical",
            azimuth_rad=1.010036549841,
            elevation_rad=0.33006189181,
            sez=self.sez,
            sensor_position=[0.44393147656176574, 1.124890532, 0.6253]
        )
        # Pre-insert required objects
        database.insertData(epoch)
        database.insertData(target_agent)
        database.insertData(sensor_agent)

        # Test insert of object via FK
        database.insertData(obs)

        # Reset DB
        database.resetData(ResonaateDatabase.VALID_DATA_TYPES)

    def testManyToOneLazyLoading(self, epoch, target_agent, sensor_agent):
        """Test many to one lazy-loading attributes."""
        julian_date = epoch.julian_date
        target_id = target_agent.unique_id
        sensor_id = sensor_agent.unique_id
        database = ResonaateDatabase.getSharedInterface()
        obs = Observation.fromSEZVector(
            epoch=epoch,
            sensor=sensor_agent,
            target=target_agent,
            sensor_type="Optical",
            azimuth_rad=1.010036549841,
            elevation_rad=0.33006189181,
            sez=self.sez,
            sensor_position=[0.44393147656176574, 1.124890532, 0.6253]
        )
        database.insertData(obs)

        new_obs = database.getData(Query(Observation), multi=False)
        # Test lazy-loading behavior for relationship() attributes
        assert new_obs.epoch.julian_date == julian_date
        assert new_obs.target.unique_id == target_id
        assert new_obs.sensor.unique_id == sensor_id

        # Reset DB
        database.resetData(ResonaateDatabase.VALID_DATA_TYPES)

    def testManyToOneQuery(self, epoch, target_agent, sensor_agent):
        """Test many to one relationship queries."""
        epoch_copy = deepcopy(epoch)
        target_copy = deepcopy(target_agent)
        sensor_copy = deepcopy(sensor_agent)

        database = ResonaateDatabase.getSharedInterface()
        obs = Observation.fromSEZVector(
            epoch=epoch,
            sensor=sensor_agent,
            target=target_agent,
            sensor_type="Optical",
            azimuth_rad=1.010036549841,
            elevation_rad=0.33006189181,
            sez=self.sez,
            sensor_position=[0.44393147656176574, 1.124890532, 0.6253]
        )
        database.insertData(obs)

        # Test querying by Target
        query = Query(Observation).filter(
            Observation.target == target_copy
        )
        new_obs = database.getData(query, multi=False)
        assert new_obs.target == target_copy

        # Test querying by Sensor
        query = Query(Observation).filter(
            Observation.sensor == sensor_copy
        )
        new_obs = database.getData(query, multi=False)
        assert new_obs.sensor == sensor_copy

        # Test querying by epoch
        query = Query(Observation).filter(
            Observation.epoch == epoch_copy
        )
        new_obs = database.getData(query, multi=False)
        assert new_obs.epoch == epoch_copy

        # Reset DB
        database.resetData(ResonaateDatabase.VALID_DATA_TYPES)
