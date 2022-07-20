from __future__ import annotations

# Standard Library Imports
from typing import TYPE_CHECKING

# Third Party Imports
import pytest
from numpy import asarray, zeros

# RESONAATE Imports
from resonaate.physics.time.stardate import JulianDate
from resonaate.scenario.config.decision_config import DecisionConfig
from resonaate.scenario.config.reward_config import RewardConfig
from resonaate.tasking.decisions import decisionFactory
from resonaate.tasking.engine.centralized_engine import CentralizedTaskingEngine
from resonaate.tasking.rewards import rewardsFactory

# Type Checking Imports
if TYPE_CHECKING:
    # RESONAATE Imports
    from resonaate.tasking.decisions import Decision
    from resonaate.tasking.rewards import Reward

sensor_nums: list[int] = [100000]
target_nums: list[int] = [10001, 10002, 10003]


@pytest.fixture(name="decision")
def getDecision() -> Decision:
    """Returns a valid Decision object."""
    decision_config = DecisionConfig(**{"name": "MunkresDecision", "parameters": {}})
    return decisionFactory(decision_config)


@pytest.fixture(name="reward")
def getReward() -> Reward:
    """Returns a valid Reward object."""
    reward_config = RewardConfig(
        **{
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
def getCentralizedEngineClass(reward: Reward, decision: Decision) -> CentralizedTaskingEngine:
    """Return reference to a minimal :class:`.Engine` class."""
    engine = CentralizedTaskingEngine(0, sensor_nums, target_nums, reward, decision, None, True)
    # engine.assess_matrix_coordinate_job_ids[1] = 0
    engine.visibility_matrix = asarray([[0, 0, 0]])
    engine.reward_matrix = asarray([[0, 0, 0]])
    engine.decision_matrix = zeros((3, 1), dtype=bool)
    return engine


def testGenerateTasking(centralized_tasking_engine: CentralizedTaskingEngine):
    """Test generateTasking()."""
    centralized_tasking_engine.generateTasking()


def testAssess(centralized_tasking_engine: CentralizedTaskingEngine):
    """Test assess()."""
    # [NOTE]: This also tests checkThreeSigmaObs() and logThreeSigmaObs() functions
    julian_date = JulianDate.getJulianDate(2019, 1, 23, 17, 42, 23.2)
    next_julian_date = JulianDate.getJulianDate(2019, 1, 23, 17, 43, 23.2)
    centralized_tasking_engine.assess(julian_date, next_julian_date)


def testGetCurrentObservation(centralized_tasking_engine: CentralizedTaskingEngine):
    """Test getCurrentObservations()."""
    centralized_tasking_engine.getCurrentObservations()
