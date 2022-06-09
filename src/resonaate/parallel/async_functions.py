"""Collection of functions to be used asynchronously for parallel execution."""
# Standard Library Imports
from pickle import loads

# Third Party Imports
from numpy import zeros, zeros_like

# Local Imports
from ..estimation.sequential.sequential_filter import FilterDebugFlag
from . import getRedisConnection


def asyncPropagate(
    dynamics, init_time, final_time, initial_state, station_keeping=None, scheduled_events=None
):
    """Wrap a dynamics propagation method for use with a parallel job submission module.

    Hint:
        The dynamics object needs to have :meth:`~.Dynamics.propagate` implemented.

    Args:
        dynamics (:class:`.Dynamics`): dynamics object to propagate
        init_time (:class:`.ScenarioTime`): initial time to propagate from
        final_time (:class:`.ScenarioTime`): time during the scenario to propagate to
        initial_state (``numpy.ndarray``): state of object before propagation
        station_keeping (``list``, optional): :class:`.StationKeeper` objects

    Returns:
        ``numpy.ndarray``: 6x1 final state vector of the object being propagated
    """
    return dynamics.propagate(
        init_time,
        final_time,
        initial_state,
        station_keeping=station_keeping,
        scheduled_events=scheduled_events,
    )


def asyncPredict(seq_filter, time, scheduled_events=None):
    """Wrap a filter prediction method for use with a parallel job submission module.

    Hint:
        The filter that's being used needs to have :meth:`~.SequentialFilter.getPredictionResult`
        and :meth:`~.SequentialFilter.updateFromAsyncResult` methods implemented.

    Args:
        seq_filter (:class:`.SequentialFilter`): filter object used to predict state estimates
        time (:class:`.ScenarioTime`): time during the scenario to predict to

    Returns:
        ``numpy.ndarray``: 6x1 final state vector of the object being propagated
    """
    seq_filter.predict(time, scheduled_events=scheduled_events)

    return seq_filter.getPredictionResult()


def asyncCalculateReward(estimate_id, reward, sensor_list):
    """Calculate an entire row in the reward matrix for each sensor tasked to a single target.

    This calculates predicted observations and their assumed reward value.

    Hint:
        The filter that's being used needs to have :meth:`~.SequentialFilter.getForecastResult`
        implemented

    Args:
        estimate_id (``int``): ID of the :class:`.EstimateAgent` to calculate metrics for.
        reward (:class:`.Reward`): function used to calculate a sensor/estimate pair's reward.
        sensor_list (``list``): sensor `unique_id` values assigned to the current tasking engine.

    Returns:
        ``dict``: reward result dictionary containts:

        :``"visibility"``: (``numpy.ndarray``): boolean array of whether each sensor can see the estimate.
        :``"reward_matrix"``: (``numpy.ndarray``): numeric reward array for each sensor.
        :``"estimate_id"``: (``int``): ID of the :class:`.EstimateAgent` to calculate metrics for.
    """
    # pylint: disable=unsupported-assignment-operation
    red = getRedisConnection()
    sensor_agents = loads(red.get("sensor_agents"))
    estimate_agents = loads(red.get("estimate_agents"))
    estimate = estimate_agents[estimate_id]

    # Ensure the visibility and reward matrices are the same scale as in the tasking engine
    visibility = zeros(len(sensor_list), dtype=bool)
    reward_matrix = zeros_like(visibility, dtype=float)

    for sensor_index, sensor_id in enumerate(sensor_list):
        sensor_agent = sensor_agents[sensor_id]

        # Attempt predicted observations, in order to perform sensor tasking
        predicted_observation_tuple = sensor_agent.sensors.makeObservation(
            estimate_id,
            estimate.state_estimate,
            estimate.visual_cross_section,
            real_obs=False,  # Don't add noise for prospective observations
        )

        # Only calculate metrics if the estimate is observable
        if predicted_observation_tuple.observation:
            # This is required to update the metrics attached to the UKF/KF for this observation
            estimate.nominal_filter.forecast([predicted_observation_tuple])
            visibility[sensor_index] = True
            reward_matrix[sensor_index] = reward(
                estimate_agents, estimate_id, sensor_agents, sensor_id
            )

    return {
        "estimate_id": estimate_id,
        "visibility": visibility,
        "reward_matrix": reward_matrix,
    }


def asyncExecuteTasking(tasked_sensors, target_id):
    """Execute tasked observations on a :class:`.TargetAgent`.

    Hint:
        The filter that's being used needs to have :meth:`~.SequentialFilter.getUpdateResult`
        implemented

    Args:
        tasked_sensors (``list``): indices corresponding to sensors tasked to observe the target.
        target_id (``int``): ID of `.TargetAgent` being tasked on.

    Returns:
        ``dict``: execute result dictionary contains:

        :``"observations"``: (``list``): successful :class:`.Observation` objects of this target.
        :``"target_id"``: (``int``): ID of the :class:`.TargetAgent` observations were made of.
    """
    successful_obs = []
    sensor_agents = loads(getRedisConnection().get("sensor_agents"))
    target_agent = loads(getRedisConnection().get("target_agents"))[target_id]
    sensor_list = list(sensor_agents.values())
    if len(tasked_sensors) > 0:
        successful_obs.extend(
            list(
                filter(  # pylint: disable=bad-builtin
                    lambda x: x.observation,
                    (
                        sensor_list[ss].sensors.makeNoisyObservation(
                            target_agent,
                        )
                        for ss in tasked_sensors
                    ),
                )
            )
        )

    return {"target_id": target_id, "observations": successful_obs}


def asyncUpdateEstimate(estimate_agent, target_agent_eci_state, successful_obs):
    """Update the state estimate for a :class:`.EstimateAgent`.

    Hint:
        The filter that's being used needs to have :meth:`~.SequentialFilter.getUpdateResult`
        and :meth:`~.SequentialFilter.updateFromAsyncResult` methods implemented.

    Args:
        estimate_agent (:class:`.EstimateAgent`): estimate object corresponding to the target.
        target_agent_eci_state (``list``): 6x1 target truth ECI state vector (debugging only).
        successful_obs (``list``): :class:`.Observation` objects to be incorporated in the filter update

    Returns:
        ``dict``: execute result dictionary contains:

        :``"filter_update"``: (``dict``): filter update results to be applied.
        :``"observations'``: (:class:`.Observation`): successful_obs
        :``"observed"``: (``bool``): whether there were successful observations of this target.
        :``"estimate_id"``: (``int``): ID of the :class:`.EstimateAgent` to calculate metrics for.
        :``"new_filter"``: (:class:`.SequentialFilter`): new filter object for this :class:`.EstimateAgent`
    """
    # Update the filter with the successful observations, save the data
    estimate_agent.updateEstimate(successful_obs, target_agent_eci_state)

    # Common result, no new filter object
    result = {
        "estimate_id": estimate_agent.simulation_id,
        "filter_update": estimate_agent.nominal_filter.getUpdateResult(),
        "observations": successful_obs,
        "observed": bool(successful_obs),
        "new_filter": None,
    }

    # MMAE is closing
    if FilterDebugFlag.ADAPTIVE_ESTIMATION_CLOSE in estimate_agent.nominal_filter.flags:
        # [NOTE]: The next two lines MUST be in this order
        estimate_agent.resetFilter(estimate_agent.nominal_filter.converged_filter)
        estimate_agent.nominal_filter.flags ^= FilterDebugFlag.ADAPTIVE_ESTIMATION_CLOSE
        result["new_filter"] = estimate_agent.nominal_filter

    # MMAE is beginning
    elif FilterDebugFlag.ADAPTIVE_ESTIMATION_START in estimate_agent.nominal_filter.flags:
        estimate_agent.nominal_filter.flags ^= FilterDebugFlag.ADAPTIVE_ESTIMATION_START
        result["new_filter"] = estimate_agent.nominal_filter

    return result
