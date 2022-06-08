# Standard Library Imports
from pickle import dumps
# Third Party Imports
from numpy import zeros, where
from sqlalchemy.orm import Query
# RESONAATE Imports
from .engine_base import TaskingEngine
from ...common.behavioral_config import BehavioralConfig
from ...common.exceptions import TaskTimeoutError
from ...common.utilities import getTimeout
from ...data.tasking_data import TaskingData
from ...data.data_interface import DataInterface, Observation, ManualSensorTask
from ...data.query_util import addAlmostEqualFilter
from ...filters.filter_debug_utils import checkThreeSigmaObs
from ...physics.time.stardate import julianDateToDatetime, JulianDate
from ...parallel import getRedisConnection
from ...parallel.async_functions import asyncCalculateReward, asyncExecuteTasking
from ...parallel.producer import QueueManager
from ...parallel.task import Task


class CentralizedTaskingEngine(TaskingEngine):
    """Centralized Tasking Engine class.

    The Centralized tasking engine provides methods for centralized network tasking processes.
    In a centralized scenario, a central process is used to collect & incorporate observations
    directly from nodes. The nodes themselves perform only a minimal amount of processing, if
    any at all.
    """

    def __init__(self, clock, sosi_network, filter_config, reward, decision, estimate_error):
        """Construct a centralized tasking engine object.

        Args:
            clock (:class:`.ScenarioClock`): clock for tracking time
            sosi_network (:class:`.SOSINetwork`): network of sensor agents
            filter_config (dict): config for the nominal filter object for tracking target agents
            reward (:class:`.Reward`): callable reward object for determining tasking priority
            decision (:class:`.Decision`): callable decision object for optimizing tasking
            estimate_error (float): variance used to generate uncertain initial estimate positions
        """
        super(CentralizedTaskingEngine, self).__init__(
            clock, sosi_network, filter_config, reward, decision, estimate_error
        )

        ## List of observations made during the current time step.
        self.cur_step_observations = []

        ## Queue manager class instance.
        self.queue_mgr = QueueManager(processed_callback=self.handleProcessedTask)

        ## Dictionary correlating submitted task IDs to
        self.assess_matrix_coordinate_task_ids = {}

        ## Dictionary correlating submitted task IDs to
        self.execute_tasking_task_ids = {}

    def handleProcessedTask(self, task):
        """Handle completed tasks via the :class:`.QueueManager` process.

        Args:
            task (:class:`.Task`): task object to be handled

        Raises:
            Exception: raised if task-tracking dicts are empty and task is handled
            Exception: raised if task completed in an error state
        """
        if task.status == 'processed':
            if self.assess_matrix_coordinate_task_ids:
                # process reward_matrix construction
                row = self.assess_matrix_coordinate_task_ids[task.id]

                self.visibility_matrix[row] = task.retval["visibility"]
                self.reward_matrix[row] = task.retval["reward_matrix"]

            elif self.execute_tasking_task_ids:
                # process execute tasking
                self.execute_tasking_task_ids[task.id].updateFromAsyncUpdateResult(
                    task.retval
                )
                self.saveObservations(task.retval["observations"])

            else:
                raise Exception("No map to handle task {0.id}.".format(task))

        else:
            raise Exception("Error occurred in task {0.id}:\n\t{0.error}".format(
                task
            ))

    def assess(self):
        """Perform desired analysis on the current simulation state.

        First, the rewards for all possible tasks are computed, then the engine optimizes
        tasking based on the reward matrix. Finally, the optimized tasking strategy is
        applied, observations are collected, and the estimate agents are updated.
        """
        # Update targets in case some are lost/added during ticToc()
        self.num_targets = len(self.target_list)

        self.constructRewardMatrix()
        self.generateTasking()
        self.executeTasking()

    def generateTasking(self):
        """Create tasking solution based on the current simulation state."""
        # With the rewards determined, make tasking decisions
        self.decision_matrix = self._decision(self.reward_matrix)

    def constructRewardMatrix(self):
        """Determine the visibility & reward matrices for the current step k."""
        self.visibility_matrix = zeros((self.num_targets, self.num_sensors), dtype=bool)
        self.reward_matrix = zeros((self.num_targets, self.num_sensors), dtype=float)

        red = getRedisConnection()
        red.set('sensor_agents', dumps(self.sensor_agents))
        red.set('estimate_agents', dumps(self.estimate_agents))

        # Determine if each sensor can observe a target. If so, save the metrics.
        for estimate_index, estimate_agent in enumerate(self.estimate_list):
            task = Task(
                asyncCalculateReward,
                args=[
                    estimate_agent.simulation_id,
                    self._reward
                ]
            )
            # [NOTE]: Value set here must be the EstimateAgent's corresponding index in
            #   viz/reward matrices
            self.assess_matrix_coordinate_task_ids[task.id] = estimate_index
            self.queue_mgr.queueTasks(task)

        # Wait for tasks to complete
        try:
            self.queue_mgr.blockUntilProcessed(
                timeout=getTimeout(self.assess_matrix_coordinate_task_ids)
            )
        except TaskTimeoutError:
            # tasks took longer to complete than expected
            msg = "Tasks haven't completed after {0} seconds."
            self.logger.error(
                msg.format(
                    5 * len(self.assess_matrix_coordinate_task_ids)
                )
            )

        # reset task handling mappings
        self.assess_matrix_coordinate_task_ids = {}

    def executeTasking(self):
        """Collect tasked observations, if they exist, based on the decision matrix.

        Collected observations are applied to each corresponding estimate agent's filter.
        """
        shared_interface = DataInterface.getSharedInterface()
        for num, (estimate, target) in enumerate(zip(self.estimate_list, self.target_list)):
            # Get any imported observations from the database
            query = Query([Observation]).filter(Observation.target_id == estimate.simulation_id)
            query = addAlmostEqualFilter(query, Observation, 'julian_date', estimate.julian_date_epoch)
            imported_observation_data = shared_interface.getData(query)

            imported_observations = []
            sensor_position_set = set()
            for observation in imported_observation_data:
                position_key = (
                    int(observation.position_lat_rad * 1000000),
                    int(observation.position_long_rad * 1000000)
                )
                if position_key not in sensor_position_set:
                    imported_observations.append(observation)
                    sensor_position_set.add(position_key)
                else:
                    msg = "Dropped duplicate observation: {observer} of {sat_num} at {timestampISO}"
                    self.logger.warning(msg.format(**observation.makeDictionary()))

            if imported_observations:
                self.logger.debug(
                    "Imported {0} observations for {1}".format(
                        len(imported_observations),
                        estimate.simulation_id
                    )
                )

            # Retrieve all the sensors tasked to this target as a tuple, so [0] is required.
            tasked_sensors = where(self.decision_matrix[num, :])[0]

            if len(tasked_sensors) > 0:
                sensor_list = {
                    sensor_agent.name for idx, sensor_agent in enumerate(self.sensor_list) if idx in tasked_sensors
                }
                self.logger.debug("Taskable sensors for RSO {0}: {1}".format(estimate.simulation_id, sensor_list))

            if len(tasked_sensors) > 0 or imported_observations:
                task = Task(
                    asyncExecuteTasking,
                    args=[
                        tasked_sensors,
                        estimate,
                        target,
                        imported_observations
                    ]
                )
                self.execute_tasking_task_ids[task.id] = estimate
                self.queue_mgr.queueTasks(task)
            else:
                # If there are no observations, there is no update information and the predicted state
                #   estimate and covariance are stored as the updated state estimate and covariance
                estimate.updateEstimate([], [])

        # Wait for tasks to complete
        try:
            self.queue_mgr.blockUntilProcessed(
                timeout=getTimeout(self.execute_tasking_task_ids)
            )
        except TaskTimeoutError:
            # tasks took longer to complete than expected
            msg = "Tasks haven't completed after {0} seconds."
            self.logger.error(
                msg.format(
                    5 * len(self.execute_tasking_task_ids)
                )
            )

        # reset task handling mappings
        self.execute_tasking_task_ids = {}

        # Check the three sigma distance of observations. Log if needed
        if BehavioralConfig.getConfig().debugging.ThreeSigmaObs:
            filenames = checkThreeSigmaObs(
                self.cur_step_observations,
                self.target_agents,
                self.sensor_agents,
                sigma=3
            )
            for filename in filenames:
                self.logger.warning("Made bad observation, debugging info:\n\t{0}".format(filename))

    def retaskSensors(self, new_estimate_agents):
        """Update the set of target agents, usually after a target is added/removed."""
        self.num_targets = len(new_estimate_agents)
        self.target_agents = new_estimate_agents

    def saveObservations(self, observations):
        """Save set of observations.

        Args:
            observations (list): List of observations to save.
        """
        self.cur_step_observations.extend(observations)

    def getCurrentObservations(self):
        """Retrieve current list of observations.

        Args:
            reset (bool,optional): Flag indicating whether to reset :attr:`.cur_step_observations` list.
        """
        observations = self.cur_step_observations
        self.cur_step_observations = []

        return observations

    def getCurrentTasking(self):
        """Return database information of current tasking."""
        for tgt_ind, target in enumerate(self.estimate_list):
            date_time = julianDateToDatetime(target.julian_date_epoch)
            for sen_ind, sensor_agent in enumerate(self.sensor_list):

                yield TaskingData(
                    julian_date=target.julian_date_epoch,
                    timestampISO=date_time.isoformat() + '.000Z',
                    target_id=target.simulation_id,
                    sensor_id=sensor_agent.simulation_id,
                    visibility=self.visibility_matrix[tgt_ind, sen_ind],
                    reward=self.reward_matrix[tgt_ind, sen_ind],
                    decision=self.decision_matrix[tgt_ind, sen_ind]
                )

    @staticmethod
    def getCurrentManualSensorTasks(current_julian_date, deconflict='max'):
        """Return a collection of the current observation tasking priorities based on given time.

        Args:
            current_julian_date (:class:`.JulianDate`, ``float``): Current Julian date/time.
            deconflict (``str``): Description of how to deconflict multiple simultaneous priorities:
                'max' = use the highest priority for the given time
                'min' = use the lowest priority for the given time

        Returns:
            ``dict``: Dictionary of current priorities keyed on RSO ID's.

        Note: 20191206 David Kusterer
            This method should be more efficient (time-wise) than `query_util::currentPriority()`
            since it results in less database queries.
        """
        if not isinstance(current_julian_date, (JulianDate, float)):
            comment = "current_julian_date argument must be of type (JulianDate, float)"
            err = "{0}, not '{1}'".format(comment, type(current_julian_date))
            raise TypeError(err)

        if isinstance(current_julian_date, JulianDate):
            current_julian_date = float(current_julian_date)

        shared_interface = DataInterface.getSharedInterface()
        query = Query([ManualSensorTask]).filter(
            ManualSensorTask.start_time <= current_julian_date,
            ManualSensorTask.end_time >= current_julian_date
        )
        current_tasks = shared_interface.getData(query)

        tasks_per_rso = {}
        for task in current_tasks:
            pre_existing = tasks_per_rso.get(task.target_id)
            if pre_existing is None:
                tasks_per_rso[task.target_id] = task.priority

            else:
                if deconflict == 'max':
                    tasks_per_rso[task.target_id] = max([pre_existing, task.priority])

                elif deconflict == 'min':
                    tasks_per_rso[task.target_id] = min([pre_existing, task.priority])

                else:
                    err = "Unexpected deconfliction strategy: '{0}'".format(deconflict)
                    raise ValueError(err)

        return tasks_per_rso
