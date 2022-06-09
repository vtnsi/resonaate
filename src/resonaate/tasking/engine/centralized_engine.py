# Standard Library Imports
# Third Party Imports
from numpy import zeros, where
from sqlalchemy.orm import Query
# RESONAATE Imports
from .engine_base import TaskingEngine
from ...common.behavioral_config import BehavioralConfig
from ...common.exceptions import JobTimeoutError
from ...common.utilities import getTimeout
from ...data.task import Task
from ...data.data_interface import Observation, ManualSensorTask
from ...data.resonaate_database import ResonaateDatabase
from ...data.query_util import addAlmostEqualFilter
from ...filters.filter_debug_utils import checkThreeSigmaObs
from ...physics.time.stardate import JulianDate
from ...parallel.async_functions import asyncCalculateReward, asyncExecuteTasking
from ...parallel.producer import QueueManager
from ...parallel.job import Job


class CentralizedTaskingEngine(TaskingEngine):
    """Centralized Tasking Engine class.

    The Centralized tasking engine provides methods for centralized network tasking processes.
    In a centralized scenario, a central process is used to collect & incorporate observations
    directly from nodes. The nodes themselves perform only a minimal amount of processing, if
    any at all.
    """

    def __init__(self, sensor_nums, target_nums, reward, decision):
        """Construct a centralized tasking engine object.

        Args:
            sensor_nums (:class:`.List`): list of sensor agents
            target_nums (:class: `.List`): list of target agents
            reward (:class:`.Reward`): callable reward object for determining tasking priority
            decision (:class:`.Decision`): callable decision object for optimizing tasking
        """
        super(CentralizedTaskingEngine, self).__init__(
            sensor_nums, target_nums, reward, decision
        )

        # Queue manager class instance.
        self.queue_mgr = QueueManager(processed_callback=self.handleProcessedJob)

        # Dictionary correlating submitted job IDs to
        self.execute_tasking_job_ids = {}

        # Dictionary correlating submitted job IDs to
        self.assess_matrix_coordinate_job_ids = {}

    def handleProcessedJob(self, job):
        """Handle completed jobs via the :class:`.QueueManager` process.

        Args:
            job (:class:`.Job`): job object to be handled

        Raises:
            Exception: raised if job-tracking dicts are empty and job is handled
            Exception: raised if job completed in an error state
        """
        if job.status == 'processed':
            if self.assess_matrix_coordinate_job_ids:
                # process reward_matrix construction
                row = self.assess_matrix_coordinate_job_ids[job.id]

                self.visibility_matrix[row] = job.retval["visibility"]
                self.reward_matrix[row] = job.retval["reward_matrix"]

            elif self.execute_tasking_job_ids:
                # process observations
                self.saveObservations(job.retval["observations"])

            else:
                raise Exception("No map to handle job {0.id}.".format(job))

        else:
            raise Exception("Error occurred in job {0.id}:\n\t{0.error}".format(
                job
            ))

    def generateTasking(self):
        """Create tasking solution based on the current simulation state."""
        # With the rewards determined, make tasking decisions
        self.decision_matrix = self._decision(self.reward_matrix)

    def constructRewardMatrix(self):
        """Determine the visibility & reward matrices for the current step k."""
        self.visibility_matrix = zeros((self.num_targets, self.num_sensors), dtype=bool)
        self.reward_matrix = zeros((self.num_targets, self.num_sensors), dtype=float)

        # Determine if each sensor can observe a target. If so, save the metrics.
        jobs = []
        for index, target in enumerate(self.target_list):
            job = Job(
                asyncCalculateReward,
                args=[
                    target,
                    self._reward,
                    self.sensor_list
                ]
            )
            # [NOTE]: Value set here must be the EstimateAgent's corresponding index in
            #   viz/reward matrices
            self.assess_matrix_coordinate_job_ids[job.id] = index
            jobs.append(job)

        self.queue_mgr.queueJobs(*jobs)

        # Wait for jobs to complete
        try:
            self.queue_mgr.blockUntilProcessed(
                timeout=getTimeout(self.assess_matrix_coordinate_job_ids)
            )
        except JobTimeoutError:
            # jobs took longer to complete than expected
            msg = "Jobs haven't completed after {0} seconds."
            self.logger.error(
                msg.format(
                    5 * len(self.assess_matrix_coordinate_job_ids)
                )
            )

        # reset job handling mappings
        self.assess_matrix_coordinate_job_ids = {}

    def executeTasking(self, julian_date):
        """Collect tasked observations, if they exist, based on the decision matrix.

        Collected observations are applied to each corresponding estimate agent's filter.

        Args:
            julian_date (:class:`.JulianDate`): epoch at which to task sensors
        """
        jobs = []
        for index, target in enumerate(self.target_list):
            # Get any imported observations from the database
            imported_observations = []
            if self._importer_db:
                imported_observations.extend(
                    self.loadImportedObservations(target, julian_date)
                )

            # Retrieve all the sensors tasked to this target as a tuple, so [0] is required.
            tasked_sensors = where(self.decision_matrix[index, :])[0]

            if len(tasked_sensors) > 0 or imported_observations:
                job = Job(
                    asyncExecuteTasking,
                    args=[
                        tasked_sensors,
                        target,
                        imported_observations
                    ]
                )
                self.execute_tasking_job_ids[job.id] = target
                jobs.append(job)

        self.queue_mgr.queueJobs(*jobs)

        # Wait for jobs to complete
        try:
            self.queue_mgr.blockUntilProcessed(
                timeout=getTimeout(self.execute_tasking_job_ids)
            )
        except JobTimeoutError:
            # jobs took longer to complete than expected
            msg = "Jobs haven't completed after {0} seconds."
            self.logger.error(
                msg.format(
                    5 * len(self.execute_tasking_job_ids)
                )
            )

        # reset job handling mappings
        self.execute_tasking_job_ids = {}

        # Check the three sigma distance of observations. Log if needed
        if BehavioralConfig.getConfig().debugging.ThreeSigmaObs:
            filenames = checkThreeSigmaObs(
                self.observations,
                sigma=3
            )
            for filename in filenames:
                self.logger.warning("Made bad observation, debugging info:\n\t{0}".format(filename))

    def loadImportedObservations(self, target_id, epoch):
        """Load imported `Observation` objects from input database.

        Args:
            target_id (``int``): ID number of the target agent
            epoch (:class:`.JulianDate`): epoch at which to query the DB for observations
        Returns:
            ``list``: :class:`.Observation` objects imported from database
        """
        query = Query([Observation]).filter(Observation.target_id == target_id)
        query = addAlmostEqualFilter(query, Observation, 'julian_date', epoch)
        imported_observation_data = self._importer_db.getData(query)

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
                    target_id
                )
            )

        return imported_observations

    def retaskSensors(self, new_estimate_nums):
        """Update the set of target agents, usually after a target is added/removed."""
        self.target_list = new_estimate_nums

    def getCurrentTasking(self, julian_date):
        """Return database information of current tasking."""
        for tgt_ind, target in enumerate(self.target_list):
            for sen_ind, sensor_agent in enumerate(self.sensor_list):

                yield Task(
                    julian_date=julian_date,
                    target_id=target,
                    sensor_id=sensor_agent,
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

            This method should be more efficient (time-wise) than `query_util::currentPriority()`
            since it results in less database queries.
        """
        if not isinstance(current_julian_date, (JulianDate, float)):
            comment = "current_julian_date argument must be of type (JulianDate, float)"
            err = "{0}, not '{1}'".format(comment, type(current_julian_date))
            raise TypeError(err)

        if isinstance(current_julian_date, JulianDate):
            current_julian_date = float(current_julian_date)

        shared_interface = ResonaateDatabase.getSharedInterface()
        query = Query(ManualSensorTask).filter(
            ManualSensorTask.start_time_jd <= current_julian_date,
            ManualSensorTask.end_time_jd >= current_julian_date
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
