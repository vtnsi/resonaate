# pylint: disable=attribute-defined-outside-init, no-self-use, unused-argument
# Standard Library Imports
import os
import pickle
# Third Party Imports
import numpy as np
import pytest
# RESONAATE Imports
try:
    from resonaate.agents.estimate_agent import EstimateAgent
    from resonaate.agents.target_agent import TargetAgent
    from resonaate.common.exceptions import MissingEphemerisError, AgentProcessingError, JobProcessingError
    from resonaate.data.importer_database import ImporterDatabase
    from resonaate.dynamics.two_body import TwoBody
    from resonaate.filters.unscented_kalman_filter import UnscentedKalmanFilter
    from resonaate.filters.statistics import Nis
    from resonaate.parallel.handlers.job_handler import JobHandler
    from resonaate.parallel.handlers.agent_propagation import AgentPropagationJobHandler
    from resonaate.parallel.job import CallbackRegistration
    from resonaate.physics.time.stardate import JulianDate, ScenarioTime
    from resonaate.scenario.clock import ScenarioClock
except ImportError as error:
    raise Exception(
        f"Please ensure you have appropriate packages installed:\n {error}"
    ) from error
# Testing Imports
from ..conftest import BaseTestCase, FIXTURE_DATA_DIR


@pytest.fixture(scope="function", name="job_handler")
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


@pytest.mark.usefixtures("redis_setup")
class TestBaseJobHandler(BaseTestCase):
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

    def testValidJob(self, job_handler, worker_manager):
        """Test executing a valid job."""
        job_handler.executeJobs()

    def testLengthyJob(self, job_handler, worker_manager, sleep_job_6s):
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


@pytest.fixture(scope="function", name="scenario_clock")
def createScenarioClock(reset_db):
    """Create a :class:`.ScenarioClock` object for use in testing."""
    clock = ScenarioClock(JulianDate(2458454.0), 300, 60)
    yield clock


@pytest.fixture(scope="function", name="target_agent")
def createTargetAgent(scenario_clock):
    """Create valid target agent for testing propagate jobs."""
    agent = TargetAgent(
        11111,
        "test_tgt",
        "Spacecraft",
        np.asarray([6378.0, 2.0, 10.0, 0.0, 0.0, 0.0]),
        scenario_clock,
        TwoBody(),
        True,
        np.diagflat([0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
    )
    yield agent


@pytest.fixture(scope="function", name="estimate_agent")
def createEstimateAgent(target_agent, scenario_clock):
    """Create valid estimate agent for testing propagate jobs."""
    agent = EstimateAgent(
        target_agent.simulation_id,
        target_agent.name,
        target_agent.agent_type,
        scenario_clock,
        np.asarray([6378.0, 2.0, 10.0, 0.0, 0.0, 0.0]),
        np.diagflat([1.0, 2.0, 1.0, 0.001, 0.002, 0.001]),
        UnscentedKalmanFilter(
            TwoBody(),
            3 * np.diagflat([1.0, 2.0, 1.0, 0.001, 0.002, 0.001]),
            Nis(0.01)
        ),
    )
    yield agent


@pytest.mark.usefixtures("redis_setup")
class TestAgentPropagateHandler(BaseTestCase):
    """Tests related to job handlers."""

    def testProblemTargetAgent(self, worker_manager, target_agent):
        """Test logging a bad agent when an error occurs."""
        handler = AgentPropagationJobHandler()
        handler.registerCallback(target_agent)
        target_scenario_time = ScenarioTime(60)
        target_julian_date = target_scenario_time.convertToJulianDate(target_agent.julian_date_epoch)

        # Spacecraft collides with Earth
        with pytest.raises(AgentProcessingError):
            handler.executeJobs(epoch_time=target_scenario_time, julian_date=target_julian_date)

    def testProblemEstimateAgent(self, redis, worker_manager, estimate_agent, target_agent):
        """Test logging a bad estimate when an error occurs."""
        redis.set('target_agents', pickle.dumps({target_agent.simulation_id: target_agent}))
        handler = AgentPropagationJobHandler()
        handler.registerCallback(estimate_agent)
        target_scenario_time = ScenarioTime(60)
        target_julian_date = target_scenario_time.convertToJulianDate(target_agent.julian_date_epoch)

        # Spacecraft collides with Earth
        with pytest.raises(AgentProcessingError):
            handler.executeJobs(epoch_time=target_scenario_time, julian_date=target_julian_date)

    def testProblemEstimateAgentNoMatch(self, redis, worker_manager, estimate_agent, target_agent):
        """Test logging a bad estimate when an error occurs, but with no matching target agent."""
        redis.set('target_agents', pickle.dumps({target_agent.simulation_id + 1: target_agent}))
        handler = AgentPropagationJobHandler()
        handler.registerCallback(estimate_agent)
        target_scenario_time = ScenarioTime(60)
        target_julian_date = target_scenario_time.convertToJulianDate(target_agent.julian_date_epoch)

        # Spacecraft collides with Earth
        with pytest.raises(AgentProcessingError):
            handler.executeJobs(epoch_time=target_scenario_time, julian_date=target_julian_date)

        # Check for log, doesn't seem to work?
        # for record_tuple in caplog.record_tuples:
        #     if "No matching TargetAgent" in record_tuple:
        #         break
        # else:
        #     assert False

    def testNoImporterDB(self, worker_manager, target_agent):
        """Test registering importer model without Importer DB created."""
        target_agent._realtime = False  # pylint: disable=protected-access
        handler = AgentPropagationJobHandler()
        with pytest.raises(ValueError):
            handler.registerCallback(target_agent)

    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testNoImporterData(self, datafiles, worker_manager, target_agent):
        """Test registering importer model without data for RSO in DB."""
        jd_start = JulianDate(2458454.0)
        epoch_time = ScenarioTime(60)
        # Create and load importer DB
        db_path = "sqlite:///" + os.path.join(datafiles, self.importer_db_path)
        importer_db = ImporterDatabase.getSharedInterface(db_path)
        importer_db.initDatabaseFromJSON(
            os.path.join(FIXTURE_DATA_DIR, self.json_rso_truth, '11111-truth.json'),
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
