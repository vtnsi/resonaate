# pylint: disable=attribute-defined-outside-init, no-self-use
# Standard Library Imports
import os
from time import sleep
# Third Party Imports
import pytest
from sqlalchemy.orm import Query
# RESONAATE Imports
try:
    from resonaate.data.data_interface import ManualSensorTask
    from resonaate.parallel import getRedisConnection, resetMaster
    from resonaate.physics.time.stardate import JulianDate
    from resonaate.services.resonaate_service import (
        ResonaateService, InitMessage, TimeTargetMessage,
        DiscontinueMessage, ManualSensorTaskMessage
    )
except ImportError as error:
    raise Exception(
        "Please ensure you have appropriate packages installed:\n {0}".format(error)
    ) from error
# Testing Imports
from ..conftest import BaseTestCase, FIXTURE_DATA_DIR


class TestResonaateService(BaseTestCase):
    """Test to exercise all aspects of the :class:`.ResonaateService` class."""

    init_msg_importer = 'json/config/init_messages/init_2018-12-1-12-0-0-importer.json'
    init_msg_realtime = 'json/config/init_messages/init_2018-12-1-12-0-0-real.json'
    init_msg_later = 'json/config/init_messages/init_2018-12-16-0-0-0.json'

    @pytest.fixture(scope="function", autouse=True)
    def fixtureSetupSericeApp(self, shared_db, monkeypatch):
        """Setup the service app and other things shared across tests.

        Note:
            This class specifically doesn't use the redis connection fixture defined in
            `conftest.py` because it requires the redis instance to be master. This is intended
            behavior because it is meant to be run as a service _across_ nodes.
        """
        with monkeypatch.context() as m_patch:
            m_patch.setattr(ResonaateService, "LOG_DROPPED_INTERVAL", 3)
            redis_conn = getRedisConnection()
            redis_conn.flushall()
            self.shared_interface = shared_db
            self.service = ResonaateService()
            yield
            self.service.stopMessageHandling(join_queue=True)
            self.service._worker_manager.stopWorkers(no_wait=True)  # pylint: disable=protected-access
            if self.shared_interface:
                del self.shared_interface
            resetMaster()

    def testDefaults(self):
        """Make sure default constructor functions as intended."""
        self.service.logger.debug("[testDefaults]")
        assert self.service.state == ResonaateService.State.UNINITIALIZED

    def testUninitializedTimeTarget(self):
        """Make sure nothing happens when time target message is sent to uninitialized service."""
        self.service.logger.debug("[testUninitializedTimeTarget]")
        target_time = JulianDate.getJulianDate(2018, 12, 1, 12, 0, 0)
        time_target_message = TimeTargetMessage(target_time)

        self.service.enqueueMessage(time_target_message)
        self.service.waitForHandler(timeout=3)
        assert self.service.state == ResonaateService.State.UNINITIALIZED

    @pytest.mark.realtime
    @pytest.mark.integration
    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testRealtimePropagation(self, datafiles):
        """Make sure that an initailzed model will propagate forward to a time target.

        Use real time propagation.
        """
        self.service.logger.debug("[testRealtimePropagation]")
        init_message = InitMessage(os.path.join(datafiles, self.init_msg_realtime))

        self.service.enqueueMessage(init_message)
        self.service.waitForHandler(timeout=3)
        assert self.service.state == ResonaateService.State.RUNNING

        target_time = JulianDate.getJulianDate(2018, 12, 1, 12, 5, 0)
        time_target_message = TimeTargetMessage(target_time)
        self.service.enqueueMessage(time_target_message)
        self.service.waitForHandler()

    @pytest.mark.importer
    @pytest.mark.integration
    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testImporterPropagation(self, datafiles):
        """Make sure that an initailzed model will propagate forward to a time target.

        Use importer model propagation.
        """
        self.service.logger.debug("[testImporterPropagation]")
        self.shared_interface.initDatabaseFromJSON(
            os.path.join(datafiles, 'json/rso_truth/11111-truth.json'),
            os.path.join(datafiles, 'json/rso_truth/11112-truth.json'),
            os.path.join(datafiles, 'json/rso_truth/11113-truth.json'),
            os.path.join(datafiles, 'json/rso_truth/11114-truth.json'),
            os.path.join(datafiles, 'json/rso_truth/11115-truth.json'),
            os.path.join(datafiles, 'json/rso_truth/11116-truth.json')
        )
        init_message = InitMessage(os.path.join(datafiles, self.init_msg_importer))

        self.service.enqueueMessage(init_message)
        self.service.waitForHandler(timeout=3)
        assert self.service.state == ResonaateService.State.RUNNING

        target_time = JulianDate.getJulianDate(2018, 12, 1, 12, 5, 0)
        time_target_message = TimeTargetMessage(target_time)
        self.service.enqueueMessage(time_target_message)
        self.service.waitForHandler()

    @pytest.mark.realtime
    @pytest.mark.integration
    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testFastForward(self, datafiles):
        """Make sure sending an init message to an running service will result in a fast-froward."""
        self.service.logger.debug("[testFastForward]")
        init_message = InitMessage(os.path.join(datafiles, self.init_msg_realtime))

        self.service.enqueueMessage(init_message)
        self.service.waitForHandler(timeout=3)
        assert self.service.state == ResonaateService.State.RUNNING

        target_time = JulianDate.getJulianDate(2018, 12, 1, 12, 1, 0)
        time_target_message = TimeTargetMessage(target_time)
        self.service.enqueueMessage(time_target_message)
        target_time = JulianDate.getJulianDate(2018, 12, 1, 12, 2, 0)
        time_target_message = TimeTargetMessage(target_time)
        self.service.enqueueMessage(time_target_message)
        target_time = JulianDate.getJulianDate(2018, 12, 1, 12, 3, 0)
        time_target_message = TimeTargetMessage(target_time)
        self.service.enqueueMessage(time_target_message)
        target_time = JulianDate.getJulianDate(2018, 12, 1, 12, 4, 0)
        time_target_message = TimeTargetMessage(target_time)
        self.service.enqueueMessage(time_target_message)
        target_time = JulianDate.getJulianDate(2018, 12, 1, 12, 5, 0)
        time_target_message = TimeTargetMessage(target_time)
        self.service.enqueueMessage(time_target_message)

        init_message = InitMessage(os.path.join(datafiles, self.init_msg_later))

        self.service.enqueueMessage(init_message)
        self.service.waitForHandler(timeout=3)

    def testManualSensorTask(self):
        """Make sure that sending a manual sensor task message results in an updated database."""
        self.service.logger.debug("[testmanualSensorTask]")
        task_message = ManualSensorTaskMessage(
            11111,
            2.0,
            JulianDate(2458454.0),
            JulianDate(2458468.5),
            "super-unique-id"
        )

        self.service.enqueueMessage(task_message)
        self.service.waitForHandler(timeout=3)

        query = Query([ManualSensorTask]).filter(
            ManualSensorTask.unique_id == 11111,
            ManualSensorTask.priority == 2.0,
            ManualSensorTask.start_time == 2458454.0,
            ManualSensorTask.end_time == 2458468.5
        )
        inserted_task = self.shared_interface.getData(query, multi=False)
        assert inserted_task is not None

    def testDroppedMessageLogging(self, caplog):
        """Make sure dropped message logging functionality works as intended."""
        # Queue first `TimeTargetMessage`
        self.service.logger.debug("[testDroppedMessageLogging]")
        target_time = JulianDate.getJulianDate(2018, 12, 1, 12, 0, 0)
        time_target_message = TimeTargetMessage(target_time)

        # Enqueue <count> copies of same `TimeTargetMessage`
        count = 5
        for _ in range(count):
            self.service.enqueueMessage(time_target_message)
        sleep(self.service.LOG_DROPPED_INTERVAL)

        # Expected log result
        expected = "Dropped {0} messages of priority '{1}' in past {2} seconds.".format(
            count,
            TimeTargetMessage.PRIORITY,
            self.service.LOG_DROPPED_INTERVAL,
        )
        # Capture logs, grab correct loggin message
        logging_msg = None
        for log_msg in caplog.messages:
            if expected in log_msg:
                logging_msg = log_msg
                break

        # Assert we have properly logged dropped messages
        assert expected in logging_msg

    @pytest.mark.realtime
    @pytest.mark.integration
    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testTimeTargetSegmentation(self, datafiles):
        """Make sure that segmenting long time targets results in successful segmentation."""
        init_message = InitMessage(os.path.join(datafiles, self.init_msg_realtime))

        self.service.enqueueMessage(init_message)
        self.service.waitForHandler(timeout=3)
        assert self.service.state == ResonaateService.State.RUNNING

        target_time = JulianDate.getJulianDate(2018, 12, 1, 12, 5, 0)
        time_target_message = TimeTargetMessage(target_time)
        self.service.enqueueMessage(time_target_message)

        self.service.waitForHandler()

    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testTimeTargetSegmentationInterrupt(self, datafiles):
        """Make sure that segmenting can be successfully interrupted."""
        init_message = InitMessage(os.path.join(datafiles, self.init_msg_realtime))

        self.service.enqueueMessage(init_message)
        self.service.waitForHandler(timeout=3)
        assert self.service.state == ResonaateService.State.RUNNING

        target_time = JulianDate.getJulianDate(2018, 12, 1, 12, 5, 0)
        time_target_message = TimeTargetMessage(target_time)
        self.service.enqueueMessage(time_target_message)

        sleep(1)
        self.service.enqueueMessage(DiscontinueMessage())

        self.service.waitForHandler()
