# pylint: disable=attribute-defined-outside-init, no-self-use
# Standard Library Imports
# Third Party Imports
import pytest
from numpy import asarray, zeros
# RESONAATE Imports
try:
    from resonaate.tasking.engine.centralized_engine import CentralizedTaskingEngine
    from resonaate.physics.time.stardate import JulianDate
except ImportError as error:
    raise Exception(
        "Please ensure you have appropriate packages installed:\n {0}".format(error)
    ) from error
# Testing Imports
from ..conftest import BaseTestCase

sensor_nums = [100000]
target_nums = [10001, 10002, 10003]


@pytest.fixture(name="centralized_tasking_engine")
def getCentralizedEngineClass(mocked_reward, mocked_decision):
    """Return reference to a minimal :class:`.Engine` class."""
    engine = CentralizedTaskingEngine(
        sensor_nums, target_nums, mocked_reward, mocked_decision
    )
    engine.assess_matrix_coordinate_task_ids[1] = 0
    engine.visibility_matrix = asarray([[0, 0, 0]])
    engine.reward_matrix = asarray([[0, 0, 0]])
    engine.decision_matrix = zeros((3, 1), dtype=bool)
    return engine


class TestCentralizedTaskingEngine(BaseTestCase):
    """Test CentralizedTaskingEngine subclass."""

    def testhandleProcessedTask(self, mocked_error_task, mocked_valid_task, centralized_tasking_engine):
        """Test handleProcessedTask(task)."""
        # [NOTE]: This also tests saveObservations()
        with pytest.raises(Exception):
            centralized_tasking_engine.handleProcessedTask(mocked_error_task)

        centralized_tasking_engine.handleProcessedTask(mocked_valid_task)

    def testGenerateTasking(self, centralized_tasking_engine):
        """Test generateTasking()."""
        centralized_tasking_engine.generateTasking()

    @pytest.mark.skip(reason="Super weird pickling error")
    def testConstructRewardMatrix(self, centralized_tasking_engine):
        """Test constructRewardMatrix()."""
        centralized_tasking_engine.constructRewardMatrix()

    def testExecuteTasking(self, centralized_tasking_engine):
        """Test executeTasking()."""
        # [NOTE]: This also tests checkThreeSigmaObs() and logThreeSigmaObs() functions
        julian_date = JulianDate.getJulianDate(2019, 1, 23, 17, 42, 23.2)
        centralized_tasking_engine.executeTasking(julian_date)

    @pytest.mark.skip(reason="Not implemented fully")
    def testRetaskSensors(self):
        """Test retaskSensors(new_estimate_agents)."""
        assert False

    def testGetCurrentObservation(self, centralized_tasking_engine):
        """Test getCurrentObservations()."""
        centralized_tasking_engine.getCurrentObservations()

    def testGetCurrentManualSensorTasks(self, centralized_tasking_engine):
        """Test getCurrentManualSensorTasks(current_julian_date)."""
        julian_date = JulianDate.getJulianDate(2019, 1, 23, 17, 42, 23.2)
        centralized_tasking_engine.getCurrentManualSensorTasks(julian_date)
