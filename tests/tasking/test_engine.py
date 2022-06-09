# pylint: disable=attribute-defined-outside-init, no-self-use
# Standard Library Imports
# Third Party Imports
import pytest
from numpy import asarray, zeros
# RESONAATE Imports
try:
    from resonaate.scenario.config.decision_config import DecisionConfig
    from resonaate.scenario.config.reward_config import RewardConfig
    from resonaate.tasking.decisions import decisionFactory
    from resonaate.tasking.rewards import rewardsFactory
    from resonaate.tasking.engine.centralized_engine import CentralizedTaskingEngine
    from resonaate.physics.time.stardate import JulianDate
except ImportError as error:
    raise Exception(
        f"Please ensure you have appropriate packages installed:\n {error}"
    ) from error
# Testing Imports
from ..conftest import BaseTestCase

sensor_nums = [100000]
target_nums = [10001, 10002, 10003]


@pytest.fixture(name="decision")
def getDecision():
    """Returns a valid Decision object."""
    decision_config = DecisionConfig()
    decision_config.readConfig({
        "name": "MunkresDecision",
        "parameters": {}
    })
    yield decisionFactory(decision_config)


@pytest.fixture(name="reward")
def getReward():
    """Returns a valid Reward object."""
    reward_config = RewardConfig()
    reward_config.readConfig({
        "name": "CostConstrainedReward",
        "metrics": [
            {
                "name": "KLDivergence",
                "parameters": {}
            },
            {
                "name": "DeltaPosition",
                "parameters": {}
            },
            {
                "name": "LyapunovStability",
                "parameters": {}
            }
        ],
        "parameters": {}
    })
    yield rewardsFactory(reward_config)


@pytest.fixture(name="centralized_tasking_engine")
def getCentralizedEngineClass(reward, decision):
    """Return reference to a minimal :class:`.Engine` class."""
    engine = CentralizedTaskingEngine(
        0, sensor_nums, target_nums, reward, decision, None, True
    )
    # engine.assess_matrix_coordinate_job_ids[1] = 0
    engine.visibility_matrix = asarray([[0, 0, 0]])
    engine.reward_matrix = asarray([[0, 0, 0]])
    engine.decision_matrix = zeros((3, 1), dtype=bool)
    yield engine


class TestCentralizedTaskingEngine(BaseTestCase):
    """Test CentralizedTaskingEngine subclass."""

    def testGenerateTasking(self, centralized_tasking_engine):
        """Test generateTasking()."""
        centralized_tasking_engine.generateTasking()

    def testAssess(self, centralized_tasking_engine):
        """Test assess()."""
        # [NOTE]: This also tests checkThreeSigmaObs() and logThreeSigmaObs() functions
        julian_date = JulianDate.getJulianDate(2019, 1, 23, 17, 42, 23.2)
        centralized_tasking_engine.assess(julian_date)

    @pytest.mark.skip(reason="Not implemented fully")
    def testRetaskSensors(self):
        """Test retaskSensors(new_estimate_agents)."""
        assert False

    def testGetCurrentObservation(self, centralized_tasking_engine):
        """Test getCurrentObservations()."""
        centralized_tasking_engine.getCurrentObservations()
