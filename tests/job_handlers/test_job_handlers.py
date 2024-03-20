from __future__ import annotations

# Standard Library Imports
import os
import pickle
import time
from typing import TYPE_CHECKING
from unittest.mock import create_autospec

# Third Party Imports
import numpy as np
import pytest
from mjolnir import Job, KeyValueStore

# RESONAATE Imports
from resonaate.common.exceptions import (
    AgentProcessingError,
    JobProcessingError,
    MissingEphemerisError,
)
from resonaate.data.importer_database import ImporterDatabase
from resonaate.job_handlers.agent_propagation import AgentPropagationJobHandler
from resonaate.job_handlers.base import CallbackRegistration, JobHandler
from resonaate.physics.time.stardate import JulianDate, ScenarioTime, julianDateToDatetime

# Local Imports
from .. import FIXTURE_DATA_DIR, IMPORTER_DB_PATH, JSON_INIT_PATH

# Type Checking Imports
if TYPE_CHECKING:
    # Standard Library Imports
    from typing import Any

    # RESONAATE Imports
    from resonaate.agents.estimate_agent import EstimateAgent
    from resonaate.agents.sensing_agent import SensingAgent
    from resonaate.agents.target_agent import TargetAgent


@pytest.fixture(name="numpy_add_job")
def getAddJob() -> Job:
    """Create Job to call np.add with [1, 2] as arguments."""
    return Job(np.add, args=[1, 2])


@pytest.fixture(name="sleep_job_6s")
def getLongSleepJob() -> Job:
    """Create Job to call time.sleep for very long time, be careful!."""
    return Job(time.sleep, args=[6])


@pytest.fixture(name="job_handler")
def createJobHandler(numpy_add_job: Job, sensor_agent: SensingAgent) -> JobHandler:
    """Create a valid JobHandler."""

    class GenericCallback(CallbackRegistration):
        """Dummy callback class for testing."""

        def jobCreateCallback(self, **kwargs) -> Job:
            """Return numpy job fixture."""
            return numpy_add_job

        def jobCompleteCallback(self, job: Job) -> Any:
            """Simply returns job result."""
            return job.retval

    class GenericJobHandler(JobHandler):
        """Dummy handler class for testing."""

        callback_class = GenericCallback

        def generateJobs(self, **kwargs) -> list[Job]:
            """Simply return list of numpy add jobs."""
            jobs = []
            for registration in self.callback_registry:
                job = registration.jobCreateCallback()
                self.job_id_registration_dict[job.id] = registration
                jobs.append(job)
            return jobs

        def deregisterCallback(self, callback_id):
            """Remove the last callback that was registered."""
            self.callback_registry.pop()

    job_handler = GenericJobHandler(dump_on_timeout=False)
    job_handler.registerCallback(sensor_agent)
    yield job_handler
    job_handler.queue_mgr.stopHandling()


@pytest.fixture(scope="class", name="mocked_error_job")
def getMockedErrorJobObject() -> Job:
    """Create a mocked error :class:`.Job` object."""
    job = create_autospec(Job, instance=True)
    job.id = 1
    job.error = "F"
    job.status = Job.Status.FAILED

    return job


class TestBaseJobHandler:
    """Tests related to job handlers."""

    def jobCallback(self, obj):
        """Dummy callback function to check the job completed."""

    def testBadRegistration(self, job_handler: JobHandler):
        """Test registering a improper callback."""
        job_handler.callback_class = self.jobCallback  # Bad callback type
        with pytest.raises(TypeError):
            job_handler.registerCallback(self)

    def testBadJob(self, job_handler: JobHandler, mocked_error_job: Job):
        """Test using a bad job with QueueManager."""
        with pytest.raises(JobProcessingError):
            job_handler.handleProcessedJob(mocked_error_job)

    def testValidJob(self, job_handler: JobHandler):
        """Test executing a valid job."""
        job_handler.executeJobs()
        assert job_handler.queue_mgr.queued_jobs_processed

    @pytest.mark.no_debug()
    def testLengthyJob(self, job_handler: JobHandler, sleep_job_6s: Job):
        """Test executing a valid job, but longer than timeout."""

        class GenericCallback(CallbackRegistration):
            """Dummy callback class for testing."""

            def jobCreateCallback(self, **kwargs) -> Job:
                """Return numpy job fixture."""
                return sleep_job_6s

            def jobCompleteCallback(self, job: Job) -> Any:
                """Simply returns job result."""
                return job.retval

        # need to do this manually for testing
        job_handler.callback_registry = [GenericCallback(self)]
        job_handler.executeJobs()
        assert not job_handler.queue_mgr.queued_jobs_processed


class TestAgentPropagateHandler:
    """Tests related to job handlers."""

    def testProblemTargetAgent(self, target_agent: TargetAgent):
        """Test logging a bad agent when an error occurs."""
        handler = AgentPropagationJobHandler()
        handler.registerCallback(target_agent)
        target_scenario_time = ScenarioTime(60)
        target_julian_date = target_scenario_time.convertToJulianDate(
            target_agent.julian_date_epoch,
        )
        prior_julian_date = ScenarioTime(0).convertToJulianDate(target_agent.julian_date_epoch)

        # Spacecraft collides with Earth
        with pytest.raises(AgentProcessingError):
            handler.executeJobs(
                epoch_time=target_scenario_time,
                prior_julian_date=prior_julian_date,
                julian_date=target_julian_date,
            )
        handler.queue_mgr.stopHandling()

    def testProblemEstimateAgent(self, estimate_agent: EstimateAgent, target_agent: TargetAgent):
        """Test logging a bad estimate when an error occurs."""
        KeyValueStore.setValue(
            "target_agents",
            pickle.dumps({target_agent.simulation_id: target_agent}),
        )
        handler = AgentPropagationJobHandler()
        handler.registerCallback(estimate_agent)
        target_scenario_time = ScenarioTime(60)
        target_julian_date = target_scenario_time.convertToJulianDate(
            target_agent.julian_date_epoch,
        )
        target_datetime = target_scenario_time.convertToDatetime(target_agent.datetime_epoch)
        prior_julian_date = ScenarioTime(0).convertToJulianDate(target_agent.julian_date_epoch)

        # Spacecraft collides with Earth
        with pytest.raises(AgentProcessingError):
            handler.executeJobs(
                epoch_time=target_scenario_time,
                prior_julian_date=prior_julian_date,
                julian_date=target_julian_date,
                datetime_epoch=target_datetime,
            )
        handler.queue_mgr.stopHandling()

    def testProblemEstimateAgentNoMatch(
        self,
        estimate_agent: EstimateAgent,
        target_agent: TargetAgent,
    ):
        """Test logging a bad estimate when an error occurs, but with no matching target agent."""
        KeyValueStore.setValue(
            "target_agents",
            pickle.dumps({target_agent.simulation_id + 1: target_agent}),
        )
        handler = AgentPropagationJobHandler()
        handler.registerCallback(estimate_agent)
        target_scenario_time = ScenarioTime(60)
        target_julian_date = target_scenario_time.convertToJulianDate(
            target_agent.julian_date_epoch,
        )
        target_datetime = target_scenario_time.convertToDatetime(target_agent.datetime_epoch)
        prior_julian_date = ScenarioTime(0).convertToJulianDate(target_agent.julian_date_epoch)

        # Spacecraft collides with Earth
        with pytest.raises(AgentProcessingError):
            handler.executeJobs(
                epoch_time=target_scenario_time,
                prior_julian_date=prior_julian_date,
                julian_date=target_julian_date,
                datetime_epoch=target_datetime,
            )
        handler.queue_mgr.stopHandling()

        # Check for log, doesn't seem to work?
        # for record_tuple in caplog.record_tuples:
        #     if "No matching TargetAgent" in record_tuple:
        #         break
        # else:
        #     assert False

    def testNoImporterDB(self, target_agent: TargetAgent):
        """Test registering importer model without Importer DB created."""
        target_agent._realtime = False
        handler = AgentPropagationJobHandler()
        error_msg = r"A valid ImporterDatabase was not established: \w+"
        with pytest.raises(ValueError, match=error_msg):
            handler.registerCallback(target_agent)
        handler.queue_mgr.stopHandling()

    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testNoImporterData(self, datafiles: str, target_agent: TargetAgent):
        """Test registering importer model without data for RSO in DB."""
        jd_start = JulianDate(2458454.0)
        epoch_time = ScenarioTime(60)
        # Create and load importer DB
        db_path = "sqlite:///" + os.path.join(datafiles, IMPORTER_DB_PATH)
        importer_db = ImporterDatabase(db_path)
        importer_db.initDatabaseFromJSON(
            os.path.join(FIXTURE_DATA_DIR, JSON_INIT_PATH, "11111-truth.json"),
            start=jd_start,
            stop=ScenarioTime(1200).convertToJulianDate(jd_start),
        )
        # Setup scenario
        target_agent._realtime = False
        handler = AgentPropagationJobHandler(importer_db_path=db_path)
        handler.registerCallback(target_agent)

        # "Register" new RSO
        handler.importer_registry[target_agent.simulation_id + 1] = target_agent.importState
        # Spacecraft collides with Earth
        j_date = epoch_time.convertToJulianDate(jd_start)
        with pytest.raises(MissingEphemerisError):
            handler.executeJobs(
                julian_date=j_date,
                epoch_time=epoch_time,
                datetime_epoch=julianDateToDatetime(j_date),
            )
        handler.queue_mgr.stopHandling()
