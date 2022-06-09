# pylint: disable=attribute-defined-outside-init, no-self-use
# Standard Library Imports
from copy import deepcopy
# Third Party Imports
import numpy as np
from sqlalchemy.orm import Query
# RESONAATE Imports
try:
    from resonaate.data.node_addition import NodeAddition
    from resonaate.data.resonaate_database import ResonaateDatabase
except ImportError as error:
    raise Exception(
        "Please ensure you have appropriate packages installed:\n {0}".format(error)
    ) from error
# Testing Imports
from ..conftest import BaseTestCase


class TestNodeAdditionTable(BaseTestCase):
    """Test class for :class:`.NodeAddition` database table class."""

    eci = [32832.44359, -26125.770428, -4175.978356, 1.920657, 2.399111, 0.090893]

    def testInit(self):
        """Test the init of NodeAddition database table."""
        _ = NodeAddition()

    def testInitKwargs(self, epoch, target_agent):
        """Test initializing the kewards of the table."""
        _ = NodeAddition(
            agent=target_agent,
            start_time=epoch,
            pos_x_km=self.eci[0],
            pos_y_km=self.eci[1],
            pos_z_km=self.eci[2],
            vel_x_km_p_sec=self.eci[3],
            vel_y_km_p_sec=self.eci[4],
            vel_z_km_p_sec=self.eci[5],
        )

    def testFromECIVector(self, epoch, target_agent):
        """Test initializing the kewards of the truth ephemeris table."""
        _ = NodeAddition.fromECIVector(
            start_time=epoch,
            agent=target_agent,
            eci=self.eci
        )

    def testReprAndDict(self, epoch, target_agent):
        """Test printing DB table object & making into dict."""
        task = NodeAddition.fromECIVector(
            start_time=epoch,
            agent=target_agent,
            eci=self.eci
        )
        print(task)
        task.makeDictionary()

    def testEquality(self, epoch, target_agent):
        """Test equals and not equals operators."""
        task1 = NodeAddition.fromECIVector(
            start_time=epoch,
            agent=target_agent,
            eci=self.eci
        )

        task2 = NodeAddition.fromECIVector(
            start_time=epoch,
            agent=target_agent,
            eci=self.eci
        )

        task3 = NodeAddition.fromECIVector(
            start_time=epoch,
            agent=target_agent,
            eci=np.asarray(self.eci) + np.asarray([0, 0, 1, 2, 3, 4])
        )

        # Test equality and inequality
        assert task1 == task2
        assert task1 != task3

    def testInsertWithRelationship(self, epoch, target_agent):
        """Test inserting node addition with related objects."""
        database = ResonaateDatabase.getSharedInterface()
        task = NodeAddition.fromECIVector(
            start_time=epoch,
            agent=target_agent,
            eci=self.eci
        )

        # Test insert of object
        database.insertData(task)

        # Reset DB
        database.resetData(ResonaateDatabase.VALID_DATA_TYPES)

    def testInsertWithForeignKeys(self, epoch, target_agent):
        """Test inserting node addition with only foreign keys."""
        database = ResonaateDatabase.getSharedInterface()
        task = NodeAddition.fromECIVector(
            start_time_jd=epoch.julian_date,
            agent_id=target_agent.unique_id,
            eci=self.eci
        )
        # Pre-insert required objects
        database.insertData(epoch)
        database.insertData(target_agent)

        # Test insert of object via FK
        database.insertData(task)

        # Reset DB
        database.resetData(ResonaateDatabase.VALID_DATA_TYPES)

    def testManyToOneLazyLoading(self, epoch, target_agent):
        """Test many to one lazy-loading attributes."""
        julian_date = epoch.julian_date
        agent_id = target_agent.unique_id
        database = ResonaateDatabase.getSharedInterface()
        task = NodeAddition.fromECIVector(
            start_time=epoch,
            agent=target_agent,
            eci=self.eci
        )
        database.insertData(task)

        new_task = database.getData(Query(NodeAddition), multi=False)
        # Test lazy-loading behavior for relationship() attributes
        assert new_task.agent.unique_id == agent_id
        assert new_task.start_time.julian_date == julian_date

        # Reset DB
        database.resetData(ResonaateDatabase.VALID_DATA_TYPES)

    def testManyToOneQuery(self, epoch, target_agent):
        """Test many to one relationship queries."""
        epoch_copy = deepcopy(epoch)
        agent_copy = deepcopy(target_agent)

        database = ResonaateDatabase.getSharedInterface()
        task = NodeAddition.fromECIVector(
            start_time=epoch,
            agent=target_agent,
            eci=self.eci
        )
        database.insertData(task)

        # Test querying by Target
        query = Query(NodeAddition).filter(
            NodeAddition.agent == agent_copy
        )
        new_task = database.getData(query, multi=False)
        assert new_task.agent == agent_copy

        # Test querying by epoch
        query = Query(NodeAddition).filter(
            NodeAddition.start_time == epoch_copy
        )
        new_task = database.getData(query, multi=False)
        assert new_task.start_time == epoch_copy

        # Reset DB
        database.resetData(ResonaateDatabase.VALID_DATA_TYPES)
