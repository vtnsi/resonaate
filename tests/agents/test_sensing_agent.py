from __future__ import annotations

# Standard Library Imports
from typing import TYPE_CHECKING
from unittest.mock import patch

# RESONAATE Imports
from resonaate.physics.time.stardate import JulianDate

if TYPE_CHECKING:
    # RESONAATE Imports
    from resonaate.agents.estimate_agent import EstimateAgent
    from resonaate.agents.sensing_agent import SensingAgent
    from resonaate.data.observation import Observation


def testUpdateObsRecord(
    observations: list[Observation],
    sensor_agent: SensingAgent,
) -> None:
    """Tests updating the sensing agent's observation record.

    Args:
        observations (list[Observation]): Dummy observation fixture
        sensor_agent (SensingAgent): Dummy sensor
    """
    obs: Observation = observations[0]
    sensor_agent._last_obs_record = {}  # Ensure no observations have been recorded
    sensor_agent.updateObsRecord(observations)
    assert sensor_agent._last_obs_record[obs.target_id] == JulianDate(obs.julian_date)


def testMinRevisit(
    sensor_agent: SensingAgent,
    observations: list[Observation],
    estimate_agent: EstimateAgent,
) -> None:
    """Tests the sensor's min_revisit_functionality.

    Args:
        sensor_agent (SensingAgent): Sensor agent fixture.
        estimate_agent (EstimateAgent): Estimate agent corresponding to the target.
        observations (list[Observation]): Fixture for obseravtions that would be generated in the collect observation step.
    """
    obs: Observation = observations[0]
    obs.julian_date = float(sensor_agent.julian_date_epoch)
    tgt_id = estimate_agent.simulation_id

    # Test for disabled case, min_revisit_time = 0
    sensor_agent.min_revisit_time = 0
    assert sensor_agent.readyToRevisit(tgt_id)

    # Enable min_revisit_time
    sensor_agent.min_revisit_time = 3600

    # Test case where no observation has been recorded
    assert sensor_agent.readyToRevisit(tgt_id)

    # Collect an observation at the current time.
    with patch.object(
        sensor_agent.sensor,
        "collectObservations",
        return_value=([obs], [], None, None),
    ):
        sensor_agent._last_obs_record = {}  # Ensure no observation record at the start.
        _, _, _, _ = sensor_agent.collectObservations(
            estimate_agent.eci_state,
            estimate_agent,  # NOTE: This is not a target agent, but it is close enough.
            [],
        )
        # Ensure that the obsevation record got updated.
        assert sensor_agent._last_obs_record[tgt_id] == JulianDate(observations[0].julian_date)

    # Move the clock forward to a point where the sensor shouldn't be ready to revisit
    sensor_agent._time += 2000
    assert not sensor_agent.readyToRevisit(tgt_id)

    # Move the clock forward again. This time to a point where we should revisit
    sensor_agent._time += 2000
    assert sensor_agent.readyToRevisit(tgt_id)
