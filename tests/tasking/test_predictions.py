"""Test suite for predicting feasible tasking."""

from __future__ import annotations

# Standard Library Imports
from typing import TYPE_CHECKING
from unittest.mock import ANY, Mock, create_autospec, patch

# RESONAATE Imports
from resonaate.data.observation import Observation
from resonaate.tasking.predictions import predictObservation

if TYPE_CHECKING:
    # RESONAATE Imports
    from resonaate.agents.estimate_agent import EstimateAgent
    from resonaate.agents.sensing_agent import SensingAgent


def testPredictObservation(mocked_sensing_agent: SensingAgent, mocked_estimate: EstimateAgent):
    """Test the `predictObservation` function.

    Args:
        mocked_sensing_agent (SensingAgent): mocked sensing agent for testing
        mocked_estimate (EstimateAgent): mocked estimate agent for testing
    """
    # Test when sensor cannot slew to the target
    mocked_sensing_agent.sensors.canSlew = Mock(return_value=False)
    predicted_observation = predictObservation(mocked_sensing_agent, mocked_estimate)

    assert predicted_observation is None
    mocked_sensing_agent.sensors.canSlew.assert_called_once()

    # Reset mock
    mocked_sensing_agent.sensors.canSlew.reset_mock()

    # Test when the sensor can slew to the target
    mocked_sensing_agent.sensors.canSlew = Mock(return_value=True)

    mocked_sensing_agent.sensors.isVisible = Mock(return_value=(False, None))
    predicted_observation = predictObservation(mocked_sensing_agent, mocked_estimate)

    assert predicted_observation is None
    mocked_sensing_agent.sensors.canSlew.assert_called_once()
    mocked_sensing_agent.sensors.isVisible.assert_called_once()

    # Reset mock
    mocked_sensing_agent.sensors.canSlew.reset_mock()
    mocked_sensing_agent.sensors.isVisible.reset_mock()

    # Test when target is visible
    mocked_sensing_agent.sensors.isVisible = Mock(return_value=(True, None))

    with patch.object(
        Observation,
        "fromMeasurement",
        return_value=create_autospec(Observation, instance=True),
    ) as mock_observation_from_measurement:
        predicted_observation = predictObservation(mocked_sensing_agent, mocked_estimate)

        assert isinstance(predicted_observation, Observation)
        mocked_sensing_agent.sensors.canSlew.assert_called_once()
        mocked_sensing_agent.sensors.isVisible.assert_called_once()
        mock_observation_from_measurement.assert_called_with(
            epoch_jd=mocked_sensing_agent.julian_date_epoch,
            target_id=mocked_estimate.simulation_id,
            tgt_eci_state=mocked_estimate.eci_state,
            sensor_id=mocked_sensing_agent.simulation_id,
            sensor_eci=mocked_sensing_agent.eci_state,
            sensor_type=ANY,
            measurement=ANY,
            noisy=False,
        )
