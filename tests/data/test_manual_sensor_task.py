# pylint: disable=attribute-defined-outside-init, no-self-use
# Standard Library Imports
from copy import deepcopy
# Third Party Imports
from sqlalchemy.orm import Query
# RESONAATE Imports
try:
    from resonaate.data.manual_sensor_task import ManualSensorTask
    from resonaate.data.resonaate_database import ResonaateDatabase
except ImportError as error:
    raise Exception(
        "Please ensure you have appropriate packages installed:\n {0}".format(error)
    ) from error
# Testing Imports
from ..conftest import BaseTestCase


class TestManualSensorTaskTable(BaseTestCase):
    """Test class for :class:`.ManualSensorTask` database table class."""

    def testInit(self):
        """Test the init of ManualSensorTask database table."""
        _ = ManualSensorTask()

    def testInitKwargs(self, epoch, target_agent):
        """Test initializing the kewards of the table."""
        _ = ManualSensorTask(
            target=target_agent,
            start_time=epoch,
            end_time_jd=epoch.julian_date + 1.0,
            priority=2.0,
            is_dynamic=True,
        )

    def testReprAndDict(self, epoch, target_agent):
        """Test printing DB table object & making into dict."""
        task = ManualSensorTask(
            target=target_agent,
            start_time=epoch,
            end_time_jd=epoch.julian_date + 1.0,
            priority=2.0,
            is_dynamic=True,
        )
        print(task)
        task.makeDictionary()

    def testEquality(self, epoch, target_agent):
        """Test equals and not equals operators."""
        task1 = ManualSensorTask(
            target=target_agent,
            start_time=epoch,
            end_time_jd=epoch.julian_date + 1.0,
            priority=2.0,
            is_dynamic=True,
        )

        task2 = ManualSensorTask(
            target=target_agent,
            start_time=epoch,
            end_time_jd=epoch.julian_date + 1.0,
            priority=2.0,
            is_dynamic=True,
        )

        task3 = ManualSensorTask(
            target=target_agent,
            start_time=epoch,
            end_time_jd=epoch.julian_date + 1.0,
            priority=2.0,
            is_dynamic=True,
        )
        task3.priority += 2

        # Test equality and inequality
        assert task1 == task2
        assert task1 != task3

    def testInsertWithRelationship(self, epoch, target_agent):
        """Test inserting manual sensor task with related objects."""
        database = ResonaateDatabase.getSharedInterface()
        task = ManualSensorTask(
            target=target_agent,
            start_time=epoch,
            end_time_jd=epoch.julian_date + 1.0,
            priority=2.0,
            is_dynamic=True,
        )

        # Test insert of object
        database.insertData(task)

        # Reset DB
        database.resetData(ResonaateDatabase.VALID_DATA_TYPES)

    def testInsertWithForeignKeys(self, epoch, target_agent):
        """Test inserting manual sensor task with only foreign keys."""
        database = ResonaateDatabase.getSharedInterface()
        task = ManualSensorTask(
            target_id=target_agent.unique_id,
            start_time_jd=epoch.julian_date,
            end_time_jd=epoch.julian_date + 1.0,
            priority=2.0,
            is_dynamic=True,
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
        task = ManualSensorTask(
            target=target_agent,
            start_time=epoch,
            end_time_jd=epoch.julian_date + 1.0,
            priority=2.0,
            is_dynamic=True,
        )
        database.insertData(task)

        new_task = database.getData(Query(ManualSensorTask), multi=False)
        # Test lazy-loading behavior for relationship() attributes
        assert new_task.target.unique_id == agent_id
        assert new_task.start_time.julian_date == julian_date

        # Reset DB
        database.resetData(ResonaateDatabase.VALID_DATA_TYPES)

    def testManyToOneQuery(self, epoch, target_agent):
        """Test many to one relationship queries."""
        epoch_copy = deepcopy(epoch)
        target_copy = deepcopy(target_agent)

        database = ResonaateDatabase.getSharedInterface()
        task = ManualSensorTask(
            target=target_agent,
            start_time=epoch,
            end_time_jd=epoch.julian_date + 1.0,
            priority=2.0,
            is_dynamic=True,
        )
        database.insertData(task)

        # Test querying by Target
        query = Query(ManualSensorTask).filter(
            ManualSensorTask.target == target_copy
        )
        new_task = database.getData(query, multi=False)
        assert new_task.target == target_copy

        # Test querying by epoch
        query = Query(ManualSensorTask).filter(
            ManualSensorTask.start_time == epoch_copy
        )
        new_task = database.getData(query, multi=False)
        assert new_task.start_time == epoch_copy

        # Reset DB
        database.resetData(ResonaateDatabase.VALID_DATA_TYPES)
