"""Collection of asynchronous functions used with the ``parallel`` submodule."""
# Standard Imports
from pickle import loads
# Third Party Imports
from numpy import zeros, zeros_like
# Package Imports
from . import getRedisConnection


def asyncPropagate(dynamics, init_time, final_time, init_state):
    """Wrap a dynamics propagation method for use with a parallel job submission module.

    Args:
        dynamics (:class:`.Dynamics`): dynamics object to propagate
        init_time (:class:`.ScenarioTime`): initial time to propagate from
        final_time (:class:`.ScenarioTime`): time during the scenario to propagate to
        init_state (``numpy.ndarray``): state of object before propagation

    Returns:
        ``numpy.ndarray``: state of the object being propagated after calculations are made
    """
    return dynamics.propagate(init_time, final_time, init_state)


def asyncPredict(_filter, time):
    """Wrap a filter prediction method for use with a parallel job submission module.

    Hint:
        The filter that's being used needs to have :meth:`~.SequentialFilter.getPredictionResult`
        and :meth:`~.SequentialFilter.updateFromAsyncResult` methods implemented.

    Args:
        _filter (:class:`.SequentialFilter`): filter object used to predict state estimates
        time (:class:`.ScenarioTime`): time during the scenario to predict to

    Returns:
        ``numpy.ndarray``: state of the object being propagated after calculations are made
    """
    _filter.predict(time)

    return _filter.getPredictionResult()


def asyncCalculateReward(estimate_id, reward):
    """Calculate an entire row in the reward matrix.

    This function calculate the rewards for each sensor tasked to a single estimate.

    Hint:
        The filter that's being used needs to have :meth:`~.SequentialFilter.getForecastResult`
        implemented

    Args:
        estimate_id (``int``): id of the :class:`.EstimateAgent` to calculate metrics for.
        reward (:class:`.Reward`): function used to calculate a sensor/estimate pair's reward.

    Returns:
        ``dict``: reward result dictionary containts:

        :``"visibility"``: (``numpy.ndarray``): boolean array of whether each sensor can see the estimate.
        :``"reward_matrix"``: (``numpy.ndarray``): numeric reward array for each sensor.
        :``"filter_update"``: (``dict``): filter forecast results to be applied.
    """
    # pylint: disable=unsupported-assignment-operation
    red = getRedisConnection()
    sensor_agents = loads(red.get('sensor_agents'))
    estimate_agents = loads(red.get('estimate_agents'))

    visibility = zeros(len(sensor_agents), dtype=bool)
    reward_matrix = zeros_like(visibility, dtype=float)

    # Circumvent custom serialization for filters that removes the 'host' field.
    estimate = estimate_agents[estimate_id]
    estimate.nominal_filter.host = estimate

    for sensor_index, (sensor_id, sensor) in enumerate(sensor_agents.items()):

        # Attempt predicted observations, in order to perform sensor tasking
        observation, _ = sensor.sensors.makeObservation(
            estimate_id,
            estimate.name,
            estimate.state_estimate,
            estimate.visual_cross_section,
            noisy=False,  # Don't add noise for prospective observations
            check_viz=True,  # We need to make sure only valid observations are included
        )

        # Only calculate metrics if the estimate is observable
        if observation:
            # This is required to update the metrics attached to the UKF/KF for this observation
            estimate.nominal_filter.forecast(observation)
            visibility[sensor_index] = True

            reward_matrix[sensor_index] = reward(estimate_agents, estimate_id, sensor_agents, sensor_id)

    return {
        'visibility': visibility,
        'reward_matrix': reward_matrix,
        'filter_update': estimate.nominal_filter.getForecastResult()
    }


def asyncExecuteTasking(tasked_sensors, estimate_agent, target_agent, imported_observations):
    """Generate observations and update the estimate for a target.

    This function executes all tasks on the given :class:`.EstimateAgent`.

    Hint:
        The filter that's being used needs to have :meth:`~.SequentialFilter.getUpdateResult`
        implemented

    Args:
        tasked_sensors (``list``): indices corresponding to sensors tasked to observe the target.
        estimate_agent (:class:`.EstimateAgent`): :class:`.EstimateAgent` object corresponding to
            the target.
        target_agent (:class:`.TargetAgent`): :class:`.TargetAgent` to task on.
        imported_observations (``list``): :class:`.Observation`s to be incorporated in the filter
            update

    Returns:
        ``dict``: execute result dictionary contains:

        :``"observations"``: (``list`` (:class:`.Observation`)): successful observations of this
            target.
        :``"filter_update"``: (``dict``): filter update results to be applied.
    """
    # Circumvent custom serialization for filters that removes the 'host' field.
    estimate_agent.nominal_filter.host = estimate_agent
    successful_obs = []
    sensor_agents = loads(getRedisConnection().get('sensor_agents'))
    sensor_list = list(sensor_agents.values())
    if len(tasked_sensors) > 0:
        successful_obs.extend(list(filter(
            None,
            (
                sensor_list[ss].sensors.makeNoisyObservation(
                    target_agent.simulation_id,
                    target_agent.name,
                    target_agent.eci_state,
                    target_agent.visual_cross_section,
                )[0] for ss in tasked_sensors
            )
        )))

    if imported_observations:
        successful_obs.extend(imported_observations)

    # Update the filter with the successful observations, save the data
    estimate_agent.updateEstimate(successful_obs, target_agent.eci_state)

    return {
        'observations': successful_obs,
        'filter_update': estimate_agent.nominal_filter.getUpdateResult()
    }
