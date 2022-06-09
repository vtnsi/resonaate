# pylint: disable=attribute-defined-outside-init
# Standard Library Imports
# Third Party Imports
import pytest
from numpy import asarray, zeros

try:
    # RESONAATE Imports
    from resonaate.physics.time.stardate import JulianDate
    from resonaate.scenario.config.decision_config import DecisionConfig
    from resonaate.scenario.config.reward_config import RewardConfig
    from resonaate.tasking.decisions import decisionFactory
    from resonaate.tasking.engine.centralized_engine import CentralizedTaskingEngine
    from resonaate.tasking.rewards import rewardsFactory
except ImportError as error:
    raise Exception(f"Please ensure you have appropriate packages installed:\n {error}") from error
# Local Imports
# Testing Imports
from ..conftest import BaseTestCase

sensor_nums = [100000]
target_nums = [10001, 10002, 10003]


@pytest.fixture(name="decision")
def getDecision():
    """Returns a valid Decision object."""
    decision_config = DecisionConfig()
    decision_config.readConfig({"name": "MunkresDecision", "parameters": {}})
    return decisionFactory(decision_config)


@pytest.fixture(name="reward")
def getReward():
    """Returns a valid Reward object."""
    reward_config = RewardConfig()
    reward_config.readConfig(
        {
            "name": "CostConstrainedReward",
            "metrics": [
                {"name": "KLDivergence", "parameters": {}},
                {"name": "DeltaPosition", "parameters": {}},
                {"name": "LyapunovStability", "parameters": {}},
            ],
            "parameters": {},
        }
    )
    return rewardsFactory(reward_config)


@pytest.fixture(name="centralized_tasking_engine")
def getCentralizedEngineClass(reward, decision):
    """Return reference to a minimal :class:`.Engine` class."""
    engine = CentralizedTaskingEngine(0, sensor_nums, target_nums, reward, decision, None, True)
    # engine.assess_matrix_coordinate_job_ids[1] = 0
    engine.visibility_matrix = asarray([[0, 0, 0]])
    engine.reward_matrix = asarray([[0, 0, 0]])
    engine.decision_matrix = zeros((3, 1), dtype=bool)
    return engine


class TestCentralizedTaskingEngine(BaseTestCase):
    """Test CentralizedTaskingEngine subclass."""

    def testGenerateTasking(self, centralized_tasking_engine):
        """Test generateTasking()."""
        centralized_tasking_engine.generateTasking()

    def testAssess(self, centralized_tasking_engine):
        """Test assess()."""
        # [NOTE]: This also tests checkThreeSigmaObs() and logThreeSigmaObs() functions
        julian_date = JulianDate.getJulianDate(2019, 1, 23, 17, 42, 23.2)
        next_julian_date = JulianDate.getJulianDate(2019, 1, 23, 17, 43, 23.2)
        centralized_tasking_engine.assess(julian_date, next_julian_date)

    def testGetCurrentObservation(self, centralized_tasking_engine):
        """Test getCurrentObservations()."""
        centralized_tasking_engine.getCurrentObservations()
