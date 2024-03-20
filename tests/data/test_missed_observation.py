from __future__ import annotations

# Standard Library Imports
from copy import deepcopy
from typing import TYPE_CHECKING

# Third Party Imports
import numpy as np
import pytest
from sqlalchemy.orm import Query

# RESONAATE Imports
from resonaate.common.labels import Explanation, SensorLabel
from resonaate.data.observation import MissedObservation

# Type Checking Imports
if TYPE_CHECKING:
    # Third Party Imports
    from numpy import ndarray

    # RESONAATE Imports
    from resonaate.data.agent import AgentModel
    from resonaate.data.epoch import Epoch
    from resonaate.data.resonaate_database import ResonaateDatabase


@pytest.fixture(name="sensor_eci")
def getSensorECI() -> ndarray:
    """Return sensor ECI state vector."""
    return np.array(
        [
            1.51388295e03,
            5.56288454e03,
            2.72049770e03,
            -4.05657378e-01,
            1.10047360e-01,
            7.12013028e-04,
        ],
    )


class TestMissedObservationTable:
    """Test class for :class:`.MissedObservation` database table class."""

    sensor_type = SensorLabel.OPTICAL

    eci = [7000.44393147656176574, 1.124890532, 0.6253, 3.0, 2.0, 1.0]  # noqa: RUF012

    def testInitKwargs(
        self,
        epoch: Epoch,
        target_agent: AgentModel,
        sensor_agent: AgentModel,
        sensor_eci: ndarray,
    ):
        """Test initializing the keywords of the table."""
        _ = MissedObservation(
            julian_date=epoch.julian_date,
            sensor_id=sensor_agent.unique_id,
            target_id=target_agent.unique_id,
            sensor_type=self.sensor_type,
            sensor_eci=sensor_eci,
            reason=Explanation.VISIBLE.value,
        )

    def testReprAndDict(
        self,
        epoch: Epoch,
        target_agent: AgentModel,
        sensor_agent: AgentModel,
        sensor_eci: ndarray,
    ):
        """Test printing DB table object & making into dict."""
        missed_ob = MissedObservation(
            julian_date=epoch.julian_date,
            sensor_id=sensor_agent.unique_id,
            target_id=target_agent.unique_id,
            sensor_type=self.sensor_type,
            sensor_eci=sensor_eci,
            reason=Explanation.MINIMUM_RANGE.value,
        )
        print(missed_ob)
        missed_ob.makeDictionary()

    def testEquality(
        self,
        epoch: Epoch,
        target_agent: AgentModel,
        sensor_agent: AgentModel,
        sensor_eci: ndarray,
    ):
        """Test equals and not equals operators."""
        obs1 = MissedObservation(
            julian_date=epoch.julian_date,
            sensor_id=sensor_agent.unique_id,
            target_id=target_agent.unique_id,
            sensor_type=self.sensor_type,
            sensor_eci=sensor_eci,
            reason=Explanation.MAXIMUM_RANGE.value,
        )

        obs2 = MissedObservation(
            julian_date=epoch.julian_date,
            sensor_id=sensor_agent.unique_id,
            target_id=target_agent.unique_id,
            sensor_type=self.sensor_type,
            sensor_eci=sensor_eci,
            reason=Explanation.MAXIMUM_RANGE.value,
        )

        obs3 = MissedObservation(
            julian_date=epoch.julian_date,
            sensor_id=sensor_agent.unique_id,
            target_id=target_agent.unique_id,
            sensor_type=self.sensor_type,
            sensor_eci=sensor_eci,
            reason=Explanation.MINIMUM_RANGE.value,
        )

        # Test equality and inequality
        assert obs1 == obs2
        assert obs1 != obs3

    def testSensorECIProperty(
        self,
        epoch: Epoch,
        target_agent: AgentModel,
        sensor_agent: AgentModel,
        sensor_eci: ndarray,
    ):
        """Test lla property."""
        obs = MissedObservation(
            julian_date=epoch.julian_date,
            sensor_id=sensor_agent.unique_id,
            target_id=target_agent.unique_id,
            sensor_type=self.sensor_type,
            sensor_eci=sensor_eci,
            reason=Explanation.LINE_OF_SIGHT.value,
        )
        assert obs.sensor_eci.shape == (6,)
        assert np.array_equal(obs.sensor_eci, sensor_eci)

    def testInsertWithRelationship(
        self,
        database: ResonaateDatabase,
        epoch: Epoch,
        target_agent: AgentModel,
        sensor_agent: AgentModel,
        sensor_eci: ndarray,
    ):
        """Test inserting MissedObservation with related objects."""
        obs = MissedObservation(
            julian_date=epoch.julian_date,
            sensor_id=sensor_agent.unique_id,
            target_id=target_agent.unique_id,
            sensor_type=self.sensor_type,
            sensor_eci=sensor_eci,
            reason=Explanation.AZIMUTH_MASK.value,
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
        """Test inserting missed observation with only foreign keys."""
        obs = MissedObservation(
            julian_date=epoch.julian_date,
            sensor_id=sensor_agent.unique_id,
            target_id=target_agent.unique_id,
            sensor_type=self.sensor_type,
            sensor_eci=sensor_eci,
            reason=Explanation.ELEVATION_MASK.value,
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
        obs = MissedObservation(
            julian_date=epoch.julian_date,
            sensor_id=sensor_agent.unique_id,
            target_id=target_agent.unique_id,
            sensor_type=self.sensor_type,
            sensor_eci=sensor_eci,
            reason=Explanation.VIZ_MAG.value,
        )
        database.insertData(epoch)
        database.insertData(target_agent)
        database.insertData(sensor_agent)
        database.insertData(obs)

        new_obs = database.getData(Query(MissedObservation), multi=False)
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

        obs = MissedObservation(
            julian_date=epoch.julian_date,
            sensor_id=sensor_agent.unique_id,
            target_id=target_agent.unique_id,
            sensor_type=self.sensor_type,
            sensor_eci=sensor_eci,
            reason=Explanation.SOLAR_FLUX.value,
        )
        database.insertData(epoch)
        database.insertData(target_agent)
        database.insertData(sensor_agent)
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
