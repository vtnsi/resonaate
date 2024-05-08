from __future__ import annotations

# Standard Library Imports
from copy import deepcopy
from typing import TYPE_CHECKING

# Third Party Imports
import numpy as np
import pytest
from sqlalchemy.orm import Query

# RESONAATE Imports
from resonaate.common.labels import SensorLabel
from resonaate.data.observation import Observation
from resonaate.physics.measurements import IsAngle, Measurement
from resonaate.physics.time.stardate import JulianDate, julianDateToDatetime
from resonaate.physics.transforms.methods import ecef2eci, lla2ecef

# Type Checking Imports
if TYPE_CHECKING:
    # Third Party Imports
    from numpy import ndarray

    # RESONAATE Imports
    from resonaate.data.agent import AgentModel
    from resonaate.data.epoch import Epoch
    from resonaate.data.resonaate_database import ResonaateDatabase


@pytest.fixture(name="sensor_eci")
def getSensorECI(epoch: Epoch) -> ndarray:
    """Convert LLA state to ECI."""
    lat_rad = 0.44393147656176574
    lon_rad = 1.124890532
    altitude_km = 0.6253
    utc_datetime = julianDateToDatetime(JulianDate(epoch.julian_date))
    return ecef2eci(lla2ecef(np.array([lat_rad, lon_rad, altitude_km])), utc_datetime)


class TestObservationTable:
    """Test class for :class:`.Observation` database table class."""

    eci = [  # noqa: RUF012
        -4957.659229144096,
        7894.2462525123365,
        3193.9292760074436,
        1.7500003208790118,
        3.931727930569842,
        -2.338646528282177,
    ]

    azimuth_rad = 1.010036549841
    elevation_rad = 0.33006189181
    sensor_type = SensorLabel.OPTICAL

    def testInitKwargs(
        self,
        epoch: Epoch,
        target_agent: AgentModel,
        sensor_agent: AgentModel,
        sensor_eci: ndarray,
    ):
        """Test initializing the keywords of the table."""
        _ = Observation(
            julian_date=epoch.julian_date,
            sensor_id=sensor_agent.unique_id,
            target_id=target_agent.unique_id,
            sensor_type=self.sensor_type,
            azimuth_rad=self.azimuth_rad,
            elevation_rad=self.elevation_rad,
            sensor_eci=sensor_eci,
            measurement=Measurement.fromMeasurementLabels(
                ["azimuth_rad", "elevation_rad"],
                np.eye(2),
            ),
        )

    def testProperties(
        self,
        epoch: Epoch,
        target_agent: AgentModel,
        sensor_agent: AgentModel,
        sensor_eci: ndarray,
    ):
        """Test property."""
        obs = Observation(
            julian_date=epoch.julian_date,
            sensor_id=sensor_agent.unique_id,
            target_id=target_agent.unique_id,
            sensor_type=self.sensor_type,
            azimuth_rad=self.azimuth_rad,
            elevation_rad=self.elevation_rad,
            sensor_eci=sensor_eci,
            measurement=Measurement.fromMeasurementLabels(
                ["azimuth_rad", "elevation_rad"],
                np.eye(2),
            ),
        )
        assert obs.sensor_eci.shape == (6,)
        assert np.array_equal(obs.sensor_eci, sensor_eci)
        assert obs.dim == 2
        assert obs.angular_values == [IsAngle.ANGLE_0_2PI, IsAngle.ANGLE_NEG_PI_PI]

    def testMeasurement(
        self,
        epoch: Epoch,
        target_agent: AgentModel,
        sensor_agent: AgentModel,
        sensor_eci: ndarray,
    ):
        """Test measurement property."""
        obs = Observation(
            julian_date=epoch.julian_date,
            sensor_id=sensor_agent.unique_id,
            target_id=target_agent.unique_id,
            sensor_type=self.sensor_type,
            azimuth_rad=self.azimuth_rad,
            elevation_rad=self.elevation_rad,
            sensor_eci=sensor_eci,
            measurement=Measurement.fromMeasurementLabels(
                ["azimuth_rad", "elevation_rad"],
                np.eye(2),
            ),
        )

        obs._measurement = None
        assert obs.measurement_states.shape == (2,)

        with pytest.raises(TypeError):
            _ = Observation(
                julian_date=epoch.julian_date,
                sensor_id=sensor_agent.unique_id,
                target_id=target_agent.unique_id,
                sensor_type=self.sensor_type,
                azimuth_rad=self.azimuth_rad,
                elevation_rad=self.elevation_rad,
                sensor_eci=sensor_eci,
                measurement=["azimuth_rad", "elevation_rad"],
            )

    def testReprAndDict(
        self,
        epoch: Epoch,
        target_agent: AgentModel,
        sensor_agent: AgentModel,
        sensor_eci: ndarray,
    ):
        """Test printing DB table object & making into dict."""
        obs = Observation(
            julian_date=epoch.julian_date,
            sensor_id=sensor_agent.unique_id,
            target_id=target_agent.unique_id,
            sensor_type=self.sensor_type,
            azimuth_rad=self.azimuth_rad,
            elevation_rad=self.elevation_rad,
            sensor_eci=sensor_eci,
            measurement=Measurement.fromMeasurementLabels(
                ["azimuth_rad", "elevation_rad"],
                np.eye(2),
            ),
        )
        print(obs)
        obs.makeDictionary()

    def testEquality(
        self,
        epoch: Epoch,
        target_agent: AgentModel,
        sensor_agent: AgentModel,
        sensor_eci: ndarray,
    ):
        """Test equals and not equals operators."""
        obs1 = Observation(
            julian_date=epoch.julian_date,
            sensor_id=sensor_agent.unique_id,
            target_id=target_agent.unique_id,
            sensor_type=self.sensor_type,
            azimuth_rad=self.azimuth_rad,
            elevation_rad=self.elevation_rad,
            sensor_eci=sensor_eci,
            measurement=Measurement.fromMeasurementLabels(
                ["azimuth_rad", "elevation_rad"],
                np.eye(2),
            ),
        )

        obs2 = Observation(
            julian_date=epoch.julian_date,
            sensor_id=sensor_agent.unique_id,
            target_id=target_agent.unique_id,
            sensor_type=self.sensor_type,
            azimuth_rad=self.azimuth_rad,
            elevation_rad=self.elevation_rad,
            sensor_eci=sensor_eci,
            measurement=Measurement.fromMeasurementLabels(
                ["azimuth_rad", "elevation_rad"],
                np.eye(2),
            ),
        )

        obs3 = Observation(
            julian_date=epoch.julian_date,
            sensor_id=sensor_agent.unique_id,
            target_id=target_agent.unique_id,
            sensor_type=self.sensor_type,
            azimuth_rad=self.azimuth_rad,
            elevation_rad=self.elevation_rad,
            sensor_eci=sensor_eci,
            measurement=Measurement.fromMeasurementLabels(
                ["azimuth_rad", "elevation_rad"],
                np.eye(2),
            ),
        )
        obs3.range_km = 500

        # Test equality and inequality
        assert obs1 == obs2
        assert obs1 != obs3

    def testMeasurementProperty(
        self,
        epoch: Epoch,
        target_agent: AgentModel,
        sensor_agent: AgentModel,
        sensor_eci: ndarray,
    ):
        """Test measurement property."""
        obs = Observation(
            julian_date=epoch.julian_date,
            sensor_id=sensor_agent.unique_id,
            target_id=target_agent.unique_id,
            sensor_type=SensorLabel.ADV_RADAR,
            azimuth_rad=1.010036549841,
            elevation_rad=0.33006189181,
            range_km=1500.0,
            range_rate_km_p_sec=0.10,
            sensor_eci=sensor_eci,
            measurement=Measurement.fromMeasurementLabels(
                ["azimuth_rad", "elevation_rad", "range_km", "range_rate_km_p_sec"],
                np.eye(4),
            ),
        )
        assert obs.measurement_states.shape == (4,)

    def testInsertWithRelationship(
        self,
        database: ResonaateDatabase,
        epoch: Epoch,
        target_agent: AgentModel,
        sensor_agent: AgentModel,
        sensor_eci: ndarray,
    ):
        """Test inserting observation with related objects."""
        obs = Observation(
            julian_date=epoch.julian_date,
            sensor_id=sensor_agent.unique_id,
            target_id=target_agent.unique_id,
            sensor_type=self.sensor_type,
            azimuth_rad=self.azimuth_rad,
            elevation_rad=self.elevation_rad,
            sensor_eci=sensor_eci,
            measurement=Measurement.fromMeasurementLabels(
                ["azimuth_rad", "elevation_rad"],
                np.eye(2),
            ),
        )

        # Test insert of object
        database.insertData(obs)

    def testInsertWithForeignKeys(
        self,
        database: ResonaateDatabase,
        epoch: Epoch,
        target_agent: AgentModel,
        sensor_agent: AgentModel,
        sensor_eci: ndarray,
    ):
        """Test inserting observation with only foreign keys."""
        obs = Observation(
            julian_date=epoch.julian_date,
            sensor_id=sensor_agent.unique_id,
            target_id=target_agent.unique_id,
            sensor_type=self.sensor_type,
            azimuth_rad=self.azimuth_rad,
            elevation_rad=self.elevation_rad,
            sensor_eci=sensor_eci,
            measurement=Measurement.fromMeasurementLabels(
                ["azimuth_rad", "elevation_rad"],
                np.eye(2),
            ),
        )
        # Pre-insert required objects
        database.insertData(epoch)
        database.insertData(target_agent)
        database.insertData(sensor_agent)

        # Test insert of object via FK
        database.insertData(obs)

    def testManyToOneLazyLoading(
        self,
        database: ResonaateDatabase,
        epoch: Epoch,
        target_agent: AgentModel,
        sensor_agent: AgentModel,
        sensor_eci: ndarray,
    ):
        """Test many to one lazy-loading attributes."""
        julian_date = epoch.julian_date
        target_id = target_agent.unique_id
        sensor_id = sensor_agent.unique_id
        obs = Observation(
            julian_date=epoch.julian_date,
            sensor_id=sensor_agent.unique_id,
            target_id=target_agent.unique_id,
            sensor_type=self.sensor_type,
            azimuth_rad=self.azimuth_rad,
            elevation_rad=self.elevation_rad,
            sensor_eci=sensor_eci,
            measurement=Measurement.fromMeasurementLabels(
                ["azimuth_rad", "elevation_rad"],
                np.eye(2),
            ),
        )
        database.insertData(epoch)
        database.insertData(target_agent)
        database.insertData(sensor_agent)
        database.insertData(obs)

        new_obs = database.getData(Query(Observation), multi=False)
        # Test lazy-loading behavior for relationship() attributes
        assert new_obs.epoch.julian_date == julian_date
        assert new_obs.target.unique_id == target_id
        assert new_obs.sensor.unique_id == sensor_id

    def testManyToOneQuery(
        self,
        database: ResonaateDatabase,
        epoch: Epoch,
        target_agent: AgentModel,
        sensor_agent: AgentModel,
        sensor_eci: ndarray,
    ):
        """Test many to one relationship queries."""
        epoch_copy = deepcopy(epoch)
        target_copy = deepcopy(target_agent)
        sensor_copy = deepcopy(sensor_agent)

        obs = Observation(
            julian_date=epoch.julian_date,
            sensor_id=sensor_agent.unique_id,
            target_id=target_agent.unique_id,
            sensor_type=self.sensor_type,
            azimuth_rad=self.azimuth_rad,
            elevation_rad=self.elevation_rad,
            sensor_eci=sensor_eci,
            measurement=Measurement.fromMeasurementLabels(
                ["azimuth_rad", "elevation_rad"],
                np.eye(2),
            ),
        )
        database.insertData(epoch)
        database.insertData(target_agent)
        database.insertData(sensor_agent)
        database.insertData(obs)

        # Test querying by Target
        query = Query(Observation).filter(Observation.target_id == target_copy.unique_id)
        new_obs = database.getData(query, multi=False)
        assert new_obs.target_id == target_copy.unique_id

        # Test querying by Sensor
        query = Query(Observation).filter(Observation.sensor_id == sensor_copy.unique_id)
        new_obs = database.getData(query, multi=False)
        assert new_obs.sensor_id == sensor_copy.unique_id

        # Test querying by epoch
        query = Query(Observation).filter(Observation.julian_date == epoch_copy.julian_date)
        new_obs = database.getData(query, multi=False)
        assert new_obs.julian_date == epoch_copy.julian_date
