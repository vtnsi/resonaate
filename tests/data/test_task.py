# pylint: disable=attribute-defined-outside-init, no-self-use
# Standard Library Imports
from copy import deepcopy
# Third Party Imports
from sqlalchemy.orm import Query
# RESONAATE Imports
try:
    from resonaate.data.resonaate_database import ResonaateDatabase
    from resonaate.data.task import Task
except ImportError as error:
    raise Exception(
        f"Please ensure you have appropriate packages installed:\n {error}"
    ) from error
# Testing Imports
from ..conftest import BaseTestCase


class TestTaskTable(BaseTestCase):
    """Test class for :class:`.Task` database table class."""

    def testInit(self):
        """Test the init of Task database table."""
        _ = Task()

    def testInitKwargs(self, epoch, target_agent, sensor_agent):
        """Test initializing the kewards of the table."""
        _ = Task(
            target=target_agent,
            sensor=sensor_agent,
            epoch=epoch,
            reward=10,
            visibility=True,
            decision=True,
        )

    def testReprAndDict(self, epoch, target_agent, sensor_agent):
        """Test printing DB table object & making into dict."""
        task = Task(
            target=target_agent,
            sensor=sensor_agent,
            epoch=epoch,
            reward=10,
            visibility=True,
            decision=True,
        )
        print(task)
        task.makeDictionary()

    def testEquality(self, epoch, target_agent, sensor_agent):
        """Test equals and not equals operators."""
        task1 = Task(
            target=target_agent,
            epoch=epoch,
            sensor=sensor_agent,
            reward=10,
            visibility=True,
            decision=True,
        )

        task2 = Task(
            target=target_agent,
            epoch=epoch,
            sensor=sensor_agent,
            reward=10,
            visibility=True,
            decision=True,
        )

        task3 = Task(
            target=target_agent,
            epoch=epoch,
            sensor=sensor_agent,
            reward=10,
            visibility=True,
            decision=True,
        )
        task3.decision = False

        # Test equality and inequality
        assert task1 == task2
        assert task1 != task3

    def testInsertWithRelationship(self, epoch, target_agent, sensor_agent):
        """Test inserting task with related objects."""
        database = ResonaateDatabase.getSharedInterface()
        task = Task(
            target=target_agent,
            epoch=epoch,
            sensor=sensor_agent,
            reward=10,
            visibility=True,
            decision=True,
        )

        # Test insert of object
        database.insertData(task)

        # Reset DB
        database.resetData(ResonaateDatabase.VALID_DATA_TYPES)

    def testInsertWithForeignKeys(self, epoch, target_agent, sensor_agent):
        """Test inserting task with only foreign keys."""
        database = ResonaateDatabase.getSharedInterface()
        task = Task(
            target_id=target_agent.unique_id,
            julian_date=epoch.julian_date,
            sensor_id=sensor_agent.unique_id,
            reward=10,
            visibility=True,
            decision=True,
        )
        # Pre-insert required objects
        database.insertData(epoch)
        database.insertData(target_agent)
        database.insertData(sensor_agent)

        # Test insert of object via FK
        database.insertData(task)

        # Reset DB
        database.resetData(ResonaateDatabase.VALID_DATA_TYPES)

    def testManyToOneLazyLoading(self, epoch, target_agent, sensor_agent):
        """Test many to one lazy-loading attributes."""
        julian_date = epoch.julian_date
        target_id = target_agent.unique_id
        sensor_id = sensor_agent.unique_id
        database = ResonaateDatabase.getSharedInterface()
        task = Task(
            target=target_agent,
            epoch=epoch,
            sensor=sensor_agent,
            reward=10,
            visibility=True,
            decision=True,
        )
        database.insertData(task)

        new_task = database.getData(Query(Task), multi=False)
        # Test lazy-loading behavior for relationship() attributes
        assert new_task.epoch.julian_date == julian_date
        assert new_task.target.unique_id == target_id
        assert new_task.sensor.unique_id == sensor_id

        # Reset DB
        database.resetData(ResonaateDatabase.VALID_DATA_TYPES)

    def testManyToOneQuery(self, epoch, target_agent, sensor_agent):
        """Test many to one relationship queries."""
        epoch_copy = deepcopy(epoch)
        target_copy = deepcopy(target_agent)
        sensor_copy = deepcopy(sensor_agent)

        database = ResonaateDatabase.getSharedInterface()
        task = Task(
            target=target_agent,
            epoch=epoch,
            sensor=sensor_agent,
            reward=10,
            visibility=True,
            decision=True,
        )
        database.insertData(task)

        # Test querying by Target
        query = Query(Task).filter(
            Task.target == target_copy
        )
        new_task = database.getData(query, multi=False)
        assert new_task.target == target_copy

        # Test querying by Sensor
        query = Query(Task).filter(
            Task.sensor == sensor_copy
        )
        new_task = database.getData(query, multi=False)
        assert new_task.sensor == sensor_copy

        # Test querying by epoch
        query = Query(Task).filter(
            Task.epoch == epoch_copy
        )
        new_task = database.getData(query, multi=False)
        assert new_task.epoch == epoch_copy

        # Reset DB
        database.resetData(ResonaateDatabase.VALID_DATA_TYPES)
