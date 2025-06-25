from __future__ import annotations

# Standard Library Imports
from unittest.mock import MagicMock, create_autospec, patch

# Third Party Imports
import pytest
import ray

# RESONAATE Imports
from resonaate.agents.estimate_agent import EstimateAgent
from resonaate.agents.sensing_agent import SensingAgent
from resonaate.data.observation import Observation
from resonaate.parallel.tasking_reward_generation import (
    RewardCalcResult,
    RewardCalcSubmission,
    asyncCalculateReward,
)
from resonaate.tasking.metrics.target import TimeSinceObservation
from resonaate.tasking.rewards.rewards import Reward, SimpleSummationReward


@pytest.fixture(name="reward")
def getReward() -> SimpleSummationReward | Reward:
    """Generates a valid reward.

    Returns:
        Reward: Valid reward object.
    """
    return SimpleSummationReward(
        [TimeSinceObservation()],
    )


@pytest.fixture(name="mocked_observation")
def getMockedObs() -> Observation:
    """Creates a mocked observation."""
    return create_autospec(Observation, instance=True)


def testAsyncCalcReward(
    mocked_estimate: EstimateAgent,
    mocked_sensing_agent: SensingAgent,
    reward: Reward,
    mocked_observation: Observation,
) -> None:
    """Tests async calc reward."""
    # Set up mocks so that the thing should be visible
    mocked_estimate.nominal_filter.forecast = MagicMock()
    mocked_sensing_agent.readyToRevisit = MagicMock(return_value=True)
    mocked_sensing_agent.sensor.predictObservation = MagicMock(
        return_value=mocked_observation,
    )

    # NOTE: The below nested functions are an attempt by me to spoof
    # ray.get and ray.put calls for purposes of testing. It is certainly hacky.
    # It actually works way better than trying to ray.put mocks ever will though.
    store: dict = {}

    def fakeRayPut(instance):
        if isinstance(instance, list):
            for item in instance:
                store[item.simulation_id] = item
            return [item.simulation_id for item in instance]
        store[instance.simulation_id] = instance
        return instance.simulation_id

    def fakeRayGet(handle):
        if isinstance(handle, list):
            return [store[item] for item in handle]
        return store.get(handle)

    with patch("ray.put", side_effect=fakeRayPut), patch("ray.get", side_effect=fakeRayGet):
        sensing_handle = ray.put(mocked_sensing_agent)
        estimate_handle = ray.put(mocked_estimate)

        submission = RewardCalcSubmission(estimate_handle, reward, [sensing_handle], 0, 0)
        result: RewardCalcResult = asyncCalculateReward._function(submission)

        # It should have been visible
        mocked_sensing_agent.readyToRevisit.assert_called_once()
        mocked_sensing_agent.sensor.predictObservation.assert_called_once()
        mocked_estimate.nominal_filter.forecast.assert_called_once()
        assert result.visibility[0]

        # Reset mocks and this time set the sensor to not be ready to revisit
        mocked_estimate.nominal_filter.forecast.reset_mock()
        mocked_sensing_agent.readyToRevisit.reset_mock()
        mocked_sensing_agent.readyToRevisit = MagicMock(return_value=False)
        mocked_sensing_agent.sensor.predictObservation.reset_mock()

        submission = RewardCalcSubmission(estimate_handle, reward, [sensing_handle], 0, 0)
        result: RewardCalcResult = asyncCalculateReward._function(submission)

        # It should not have been visible
        mocked_sensing_agent.readyToRevisit.assert_called_once()
        mocked_sensing_agent.sensor.predictObservation.assert_not_called()
        mocked_estimate.nominal_filter.forecast.assert_not_called()
        assert not result.visibility[0]
