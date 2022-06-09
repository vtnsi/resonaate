# pylint: disable=attribute-defined-outside-init
# Standard Library Imports
import os
from time import sleep

# Third Party Imports
import pytest
from sqlalchemy.orm import Query

try:
    # RESONAATE Imports
    from resonaate.data.events import TargetTaskPriority
    from resonaate.data.importer_database import ImporterDatabase
    from resonaate.physics.time.stardate import JulianDate
    from resonaate.scenario.config import ScenarioConfig
    from resonaate.services.resonaate_service import (
        DiscontinueMessage,
        InitMessage,
        ManualSensorTaskMessage,
        ResonaateService,
        TimeTargetMessage,
    )
except ImportError as error:
    raise Exception(f"Please ensure you have appropriate packages installed:\n {error}") from error
# Local Imports
# Testing Imports
from ..conftest import FIXTURE_DATA_DIR, BaseTestCase


@pytest.mark.service()
class TestResonaateService(BaseTestCase):
    """Test to exercise all aspects of the :class:`.ResonaateService` class."""

    init_msg_importer = os.path.join(
        BaseTestCase.json_init_path, "init_2018-12-1-12-0-0-importer.json"
    )
    init_msg_realtime = os.path.join(
        BaseTestCase.json_init_path, "init_2018-12-1-12-0-0-real.json"
    )
    init_msg_later = os.path.join(BaseTestCase.json_init_path, "init_2018-12-16-0-0-0.json")

    @pytest.fixture(autouse=True)
    def _fixtureSetupSericeApp(
        self, monkeypatch, reset_shared_db
    ):  # pylint: disable=unused-argument
        """Setup the service app and other things shared across tests.

        Note:
            This class specifically doesn't use the redis connection fixture defined in
            `conftest.py` because it requires the redis instance to be master. This is intended
            behavior because it is meant to be run as a service _across_ nodes.
        """
        with monkeypatch.context() as m_patch:
            m_patch.setattr(ResonaateService, "LOG_DROPPED_INTERVAL", 3)
            self.service = ResonaateService()
            yield
            self.service.shutdown(flushall=True)

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
        self.service.waitForHandler(timeout=15)
        assert self.service.state == ResonaateService.State.UNINITIALIZED

    @pytest.mark.realtime()
    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testRealtimePropagation(self, datafiles):
        """Make sure that an initailzed model will propagate forward to a time target.

        Use real time propagation.
        """
        self.service.logger.debug("[testRealtimePropagation]")
        init_message = InitMessage(
            ScenarioConfig.parseConfigFile(os.path.join(datafiles, self.init_msg_realtime))
        )

        self.service.enqueueMessage(init_message)
        self.service.waitForHandler(timeout=3)
        assert self.service.state == ResonaateService.State.RUNNING

        target_time = JulianDate.getJulianDate(2018, 12, 1, 12, 5, 0)
        time_target_message = TimeTargetMessage(target_time)
        self.service.enqueueMessage(time_target_message)
        assert self.service.waitForHandler(timeout=30) is True

    @pytest.mark.importer()
    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testImporterPropagation(
        self, datafiles, reset_importer_db
    ):  # pylint: disable=unused-argument
        """Make sure that an initailzed model will propagate forward to a time target.

        Use importer model propagation.
        """
        self.service.logger.debug("[testImporterPropagation]")
        importer_db_url = "sqlite:///" + os.path.join(datafiles, self.importer_db_path)
        importer_db = ImporterDatabase.getSharedInterface(importer_db_url)
        importer_db.initDatabaseFromJSON(
            os.path.join(datafiles, self.json_rso_truth, "11111-truth.json"),
            os.path.join(datafiles, self.json_rso_truth, "11112-truth.json"),
            os.path.join(datafiles, self.json_rso_truth, "11113-truth.json"),
            os.path.join(datafiles, self.json_rso_truth, "11114-truth.json"),
            os.path.join(datafiles, self.json_rso_truth, "11115-truth.json"),
            os.path.join(datafiles, self.json_rso_truth, "11116-truth.json"),
        )
        init_message = InitMessage(
            ScenarioConfig.parseConfigFile(os.path.join(datafiles, self.init_msg_importer))
        )

        self.service.enqueueMessage(init_message)
        self.service.waitForHandler(timeout=3)
        assert self.service.state == ResonaateService.State.RUNNING

        target_time = JulianDate.getJulianDate(2018, 12, 1, 12, 5, 0)
        time_target_message = TimeTargetMessage(target_time)
        self.service.enqueueMessage(time_target_message)
        assert self.service.waitForHandler(timeout=30) is True

    @pytest.mark.realtime()
    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testFastForward(self, datafiles):
        """Make sure sending an init message to an running service will result in a fast-froward."""
        self.service.logger.debug("[testFastForward]")
        init_message = InitMessage(
            ScenarioConfig.parseConfigFile(os.path.join(datafiles, self.init_msg_realtime))
        )

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

        init_message = InitMessage(
            ScenarioConfig.parseConfigFile(os.path.join(datafiles, self.init_msg_later))
        )

        self.service.enqueueMessage(init_message)
        assert self.service.waitForHandler(timeout=15) is True

    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testManualSensorTask(self, datafiles, database):
        """Make sure that sending a manual sensor task message results in an updated database."""
        self.service.logger.debug("[testmanualSensorTask]")
        init_message = InitMessage(
            ScenarioConfig.parseConfigFile(os.path.join(datafiles, self.init_msg_realtime))
        )

        self.service.enqueueMessage(init_message)
        self.service.waitForHandler(timeout=3)

        task_message = ManualSensorTaskMessage(
            11111,
            2.0,
            JulianDate.getJulianDate(2018, 12, 1, 12, 0, 0),
            JulianDate.getJulianDate(2018, 12, 1, 12, 6, 0),
            "super-unique-id",
        )

        self.service.enqueueMessage(task_message)
        self.service.waitForHandler(timeout=3)

        # pylint: disable=comparison-with-callable
        query = Query(TargetTaskPriority).filter(
            TargetTaskPriority.agent_id == task_message.target_id,
            TargetTaskPriority.priority == task_message.obs_priority,
            TargetTaskPriority.start_time_jd == task_message.start_time,
            TargetTaskPriority.end_time_jd == task_message.end_time,
        )
        inserted_task = database.getData(query, multi=False)  # pylint: disable=protected-access
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
        expected = f"Dropped {count} messages of priority '{TimeTargetMessage.PRIORITY}'"
        expected += f" in past {self.service.LOG_DROPPED_INTERVAL} seconds."
        # Capture logs, grab correct loggin message
        logging_msg = None
        for log_msg in caplog.messages:
            if expected in log_msg:
                logging_msg = log_msg
                break

        # Assert we have properly logged dropped messages
        assert expected in logging_msg

    @pytest.mark.realtime()
    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testTimeTargetSegmentation(self, datafiles):
        """Make sure that segmenting long time targets results in successful segmentation."""
        init_message = InitMessage(
            ScenarioConfig.parseConfigFile(os.path.join(datafiles, self.init_msg_realtime))
        )

        self.service.enqueueMessage(init_message)
        self.service.waitForHandler(timeout=3)
        assert self.service.state == ResonaateService.State.RUNNING

        target_time = JulianDate.getJulianDate(2018, 12, 1, 12, 5, 0)
        time_target_message = TimeTargetMessage(target_time)
        self.service.enqueueMessage(time_target_message)

        assert self.service.waitForHandler(timeout=30) is True

    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testTimeTargetSegmentationInterrupt(self, datafiles):
        """Make sure that segmenting can be successfully interrupted."""
        init_message = InitMessage(
            ScenarioConfig.parseConfigFile(os.path.join(datafiles, self.init_msg_realtime))
        )

        self.service.enqueueMessage(init_message)
        self.service.waitForHandler(timeout=3)
        assert self.service.state == ResonaateService.State.RUNNING

        target_time = JulianDate.getJulianDate(2018, 12, 1, 12, 5, 0)
        time_target_message = TimeTargetMessage(target_time)
        self.service.enqueueMessage(time_target_message)

        sleep(1)
        self.service.enqueueMessage(DiscontinueMessage())

        assert self.service.waitForHandler(timeout=30) is True
