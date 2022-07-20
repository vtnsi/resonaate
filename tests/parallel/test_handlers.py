# pylint: disable=unused-argument
from __future__ import annotations

# Standard Library Imports
import os
import pickle
from unittest.mock import create_autospec

# Third Party Imports
import numpy as np
import pytest

# RESONAATE Imports
from resonaate.agents.estimate_agent import EstimateAgent
from resonaate.agents.target_agent import TargetAgent
from resonaate.common.exceptions import (
    AgentProcessingError,
    JobProcessingError,
    MissingEphemerisError,
)
from resonaate.data.importer_database import ImporterDatabase
from resonaate.dynamics.two_body import TwoBody
from resonaate.estimation.maneuver_detection import StandardNis
from resonaate.estimation.sequential.unscented_kalman_filter import UnscentedKalmanFilter
from resonaate.parallel.handlers.agent_propagation import AgentPropagationJobHandler
from resonaate.parallel.handlers.job_handler import JobHandler
from resonaate.parallel.job import CallbackRegistration, Job
from resonaate.physics.time.stardate import JulianDate, ScenarioTime
from resonaate.scenario.clock import ScenarioClock

# Local Imports
from ..conftest import FIXTURE_DATA_DIR, IMPORTER_DB_PATH, JSON_INIT_PATH


@pytest.fixture(name="job_handler")
def createJobHandler(numpy_add_job, mocked_sensing_agent):
    """Create a valid JobHandler."""

    class GenericCallback(CallbackRegistration):
        """Dummy callback class for testing."""

        def jobCreateCallback(self, **kwargs):
            """Return numpy job fixture."""
            return numpy_add_job

        def jobCompleteCallback(self, job):
            """Simply returns job result."""
            return job.retval

    class GenericJobHandler(JobHandler):
        """Dummy handler class for testing."""

        callback_class = GenericCallback

        def generateJobs(self, **kwargs):
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

    job_handler = GenericJobHandler()
    job_handler.registerCallback(mocked_sensing_agent)
    yield job_handler
    job_handler.queue_mgr.close()


@pytest.fixture(scope="class", name="mocked_error_job")
def getMockedErrorJobObject() -> Job:
    """Create a mocked error :class:`.Job` object."""
    job = create_autospec(Job)
    job.id = 1
    job.error = "F"

    return job


@pytest.mark.usefixtures("redis_setup", "worker_manager")
class TestBaseJobHandler:
    """Tests related to job handlers."""

    def jobCallback(self, obj):
        """Dummy callback function to check the job completed."""

    def testBadRegistration(self, job_handler):
        """Test registering a improper callback."""
        job_handler.callback_class = self.jobCallback  # Bad callback type
        with pytest.raises(TypeError):
            job_handler.registerCallback(self)

    def testBadJob(self, job_handler, mocked_error_job):
        """Test using a bad job with QueueManager."""
        with pytest.raises(JobProcessingError):
            job_handler.handleProcessedJob(mocked_error_job)

    def testValidJob(self, job_handler):
        """Test executing a valid job."""
        job_handler.executeJobs()

    def testLengthyJob(self, job_handler, sleep_job_6s):
        """Test executing a valid job, but longer than timeout."""

        class GenericCallback(CallbackRegistration):
            """Dummy callback class for testing."""

            def jobCreateCallback(self, **kwargs):
                """Return numpy job fixture."""
                return sleep_job_6s

            def jobCompleteCallback(self, job):
                """Simply returns job result."""
                return job.retval

        # need to do this manually for testing
        job_handler.callback_registry = [GenericCallback(self)]
        job_handler.executeJobs()

        # Check for log, doesn't seem to work?
        # for record_tuple in caplog.record_tuples:
        #     if "completed after" in record_tuple:
        #         break
        # else:
        #     assert False


@pytest.fixture(name="scenario_clock")
def createScenarioClock(reset_shared_db):
    """Create a :class:`.ScenarioClock` object for use in testing."""
    return ScenarioClock(JulianDate(2458454.0), 300, 60)


@pytest.fixture(name="target_agent")
def createTargetAgent(scenario_clock):
    """Create valid target agent for testing propagate jobs."""
    agent = TargetAgent(
        11111,
        "test_tgt",
        "Spacecraft",
        np.asarray([400.0, 2.0, 10.0, 0.0, 0.0, 0.0]),
        scenario_clock,
        TwoBody(),
        True,
        np.diagflat([0.0, 0.0, 0.0, 0.0, 0.0, 0.0]),
        25.0,
        500.0,
        0.21,
    )
    return agent


@pytest.fixture(name="estimate_agent")
def createEstimateAgent(target_agent, scenario_clock):
    """Create valid estimate agent for testing propagate jobs."""
    est_x = np.asarray([6378.0, 2.0, 10.0, 0.0, 0.0, 0.0])
    est_p = np.diagflat([1.0, 2.0, 1.0, 0.001, 0.002, 0.001])
    agent = EstimateAgent(
        target_agent.simulation_id,
        target_agent.name,
        target_agent.agent_type,
        scenario_clock,
        est_x,
        est_p,
        UnscentedKalmanFilter(
            target_agent.simulation_id,
            scenario_clock.time,
            est_x,
            est_p,
            TwoBody(),
            3 * est_p,
            StandardNis(0.01),
            None,
        ),
        None,
        25.0,
        500.0,
        0.21,
    )
    return agent


@pytest.mark.usefixtures("redis_setup", "worker_manager")
class TestAgentPropagateHandler:
    """Tests related to job handlers."""

    def testProblemTargetAgent(self, target_agent):
        """Test logging a bad agent when an error occurs."""
        handler = AgentPropagationJobHandler()
        handler.registerCallback(target_agent)
        target_scenario_time = ScenarioTime(60)
        target_julian_date = target_scenario_time.convertToJulianDate(
            target_agent.julian_date_epoch
        )
        prior_julian_date = ScenarioTime(0).convertToJulianDate(target_agent.julian_date_epoch)

        # Spacecraft collides with Earth
        with pytest.raises(AgentProcessingError):
            handler.executeJobs(
                epoch_time=target_scenario_time,
                prior_julian_date=prior_julian_date,
                julian_date=target_julian_date,
            )

    def testProblemEstimateAgent(self, redis, estimate_agent, target_agent):
        """Test logging a bad estimate when an error occurs."""
        redis.set("target_agents", pickle.dumps({target_agent.simulation_id: target_agent}))
        handler = AgentPropagationJobHandler()
        handler.registerCallback(estimate_agent)
        target_scenario_time = ScenarioTime(60)
        target_julian_date = target_scenario_time.convertToJulianDate(
            target_agent.julian_date_epoch
        )
        prior_julian_date = ScenarioTime(0).convertToJulianDate(target_agent.julian_date_epoch)

        # Spacecraft collides with Earth
        with pytest.raises(AgentProcessingError):
            handler.executeJobs(
                epoch_time=target_scenario_time,
                prior_julian_date=prior_julian_date,
                julian_date=target_julian_date,
            )

    def testProblemEstimateAgentNoMatch(self, redis, estimate_agent, target_agent):
        """Test logging a bad estimate when an error occurs, but with no matching target agent."""
        redis.set("target_agents", pickle.dumps({target_agent.simulation_id + 1: target_agent}))
        handler = AgentPropagationJobHandler()
        handler.registerCallback(estimate_agent)
        target_scenario_time = ScenarioTime(60)
        target_julian_date = target_scenario_time.convertToJulianDate(
            target_agent.julian_date_epoch
        )
        prior_julian_date = ScenarioTime(0).convertToJulianDate(target_agent.julian_date_epoch)

        # Spacecraft collides with Earth
        with pytest.raises(AgentProcessingError):
            handler.executeJobs(
                epoch_time=target_scenario_time,
                prior_julian_date=prior_julian_date,
                julian_date=target_julian_date,
            )

        # Check for log, doesn't seem to work?
        # for record_tuple in caplog.record_tuples:
        #     if "No matching TargetAgent" in record_tuple:
        #         break
        # else:
        #     assert False

    def testNoImporterDB(self, target_agent):
        """Test registering importer model without Importer DB created."""
        target_agent._realtime = False  # pylint: disable=protected-access
        handler = AgentPropagationJobHandler()
        error_msg = r"A valid ImporterDatabase was not established: \w+"
        with pytest.raises(ValueError, match=error_msg):
            handler.registerCallback(target_agent)

    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testNoImporterData(self, datafiles, target_agent, reset_importer_db):
        """Test registering importer model without data for RSO in DB."""
        jd_start = JulianDate(2458454.0)
        epoch_time = ScenarioTime(60)
        # Create and load importer DB
        db_path = "sqlite:///" + os.path.join(datafiles, IMPORTER_DB_PATH)
        importer_db = ImporterDatabase.getSharedInterface(db_path)
        importer_db.initDatabaseFromJSON(
            os.path.join(FIXTURE_DATA_DIR, JSON_INIT_PATH, "11111-truth.json"),
            start=jd_start,
            stop=ScenarioTime(1200).convertToJulianDate(jd_start),
        )
        # Setup scenario
        target_agent._realtime = False  # pylint: disable=protected-access
        handler = AgentPropagationJobHandler(importer_db_path=db_path)
        handler.registerCallback(target_agent)

        # "Register" new RSO
        handler.importer_registry[target_agent.simulation_id + 1] = target_agent.importState
        # Spacecraft collides with Earth
        j_date = epoch_time.convertToJulianDate(jd_start)
        with pytest.raises(MissingEphemerisError):
            handler.executeJobs(julian_date=j_date, epoch_time=epoch_time)
