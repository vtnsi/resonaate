# Standard Library Imports
import logging
import os.path
from pickle import dumps
from collections import defaultdict
# Third Party Imports
from numpy import around, seterr, asarray
from numpy.random import default_rng
from scipy.linalg import norm
from sqlalchemy.orm import Query
# RESONAATE Imports
from .scenario_builder import ScenarioBuilder
from ..agents.estimate_agent import EstimateAgent
from ..agents.target_agent import TargetAgent
from ..common.behavioral_config import BehavioralConfig
from ..common.exceptions import TaskTimeoutError
from ..common.logger import Logger
from ..common.utilities import loadJSONFile, loadYAMLFile, getTimeout
from ..data.data_interface import DataInterface
from ..data.node_addition import NodeAddition
from ..data.query_util import addAlmostEqualFilter
from ..dynamics import spacecraftDynamicsFactory
from ..parallel import getRedisConnection, REDIS_QUEUE_LOGGER
from ..parallel.async_functions import asyncUpdateEstimate
from ..parallel.job_handler import PropagateJobHandler, CallbackRegistration
from ..parallel.producer import QueueManager
from ..parallel.task import Task
from ..parallel.worker import WorkerManager
from ..physics.noise import noiseCovarianceFactory


class Scenario:
    """Simulation scenario class for managing .

    The Scenario class is the main simulation object that contains the major simulation pieces. It
    handles stepping the simulation forward, updating the simulation objects, and outputting data.
    This class serves as a "public" API for running RESONAATE simulations.
    """

    def __init__(
            self, config, clock, target_agents,
            estimate_agents, sensor_network, tasking_engines, _filter, logger=None, start_workers=True
    ):
        """Instantiate a Scenario object.

        Args:
            config (:class:`.ScenarioConfig`): configuration used to create this instance, kept for reference.
            clock (:class:`.ScenarioClock`): main clock object for tracking time & managing tasking queues
            target_agents (``dict``): target RSO objects for this :class:`.Scenario` .
            estimate_agents (``dict``): estimate RSO objects for this :class:`.Scenario` .
            sensor_network (``list``): sensor network for this :class:`.Scenario` .
            tasking_engines (:class:`.TaskingEngine`): list of tasking engines for this :class:`.Scenario` .
            _filter (:class:`.SequentialFilter`): kalman filter for this "class:`.Scenario` .
            logger (:class:`.Logger`, optional):pPreviously instantiated :class:`.Logger` instance to be used.
                Defaults to `None`, resulting in the class instantiating its own :class:`.Logger`.
            start_workers (``bool``, optional): Flag indicating whether this :class:`.Scenario` should
                spin up its own :class:`.WorkerManager` instance or not. Defaults to ``True``.
        """
        # Save scenario configuration
        self.scenario_config = config

        # Save the clock object
        self.clock = clock

        # Save target_agents, estimate_agents, sensor network, tasking engine and filter
        self.target_agents = target_agents
        self._estimate_agents = estimate_agents
        self.sensor_network = sensor_network
        self._sensor_agents = {node.simulation_id: node for node in self.sensor_network}
        self._tasking_engines = tasking_engines
        self.filter = _filter
        self.current_julian_date = self.julian_date_start

        # Queue manager class instance.
        self.queue_mgr = QueueManager(processed_callback=self.handleProcessedTask)

        # Dictionary correlating submitted task IDs to
        self.execute_tasking_task_ids = {}

        # Save filter dynamics functions
        self._dynamics_method = spacecraftDynamicsFactory(
            config.propagation["propagation_model"],
            self.clock,
            config.geopotential,
            config.perturbations,
            method=config.propagation["integration_method"]
        )

        # Save filter & dynamics process noise matrix
        self._filter_noise_matrix = noiseCovarianceFactory(
            config.noise["filter_noise_type"],
            config.time["physics_step_sec"],
            config.noise["filter_noise_magnitude"]
        )

        self._dynamics_noise_matrix = noiseCovarianceFactory(
            config.noise["dynamics_noise_type"],
            config.time["physics_step_sec"],
            config.noise["dynamics_noise_magnitude"]
        )

        ## Logging class used to track execution.
        self.logger = logger
        if logger is None:
            self.logger = Logger("resonaate", path=BehavioralConfig.getConfig().logging.OutputLocation)

        if BehavioralConfig.getConfig().debugging.ParallelDebugMode:
            self.logger.warning("Simulation is running in debug mode. Worker tasks can block indefinitely.")

        REDIS_QUEUE_LOGGER.setLevel(logging.WARNING)
        if start_workers:
            ## Worker manager class instance.
            self.worker_mgr = WorkerManager(daemonic=True)
            self.worker_mgr.startWorkers()

        # Log some basic information about propagation for this simulation
        self.logger.info("Filter process noise magnitude: {0}".format(norm(self._filter_noise_matrix)))
        self.logger.info("Dynamics process noise magnitude: {0}".format(norm(self._dynamics_noise_matrix)))
        self.logger.info("Random seed: {0}".format(config.noise["random_seed"]))
        self.logger.info(
            "Using real-time propagation for truth data: {0}".format(config.propagation["realtime_propagation"])
        )
        self.logger.info("Spacecraft dynamics model: {0}".format(config.propagation["propagation_model"]))
        self.logger.info("Numerical integration method: {0}".format(config.propagation["integration_method"]))
        self.logger.info("Earth gravity model: {0}".format(config.geopotential["model"]))
        self.logger.info(
            "Earth geopotential degree, order: {0}, {1}".format(
                config.geopotential["degree"],
                config.geopotential["order"]
            )
        )
        if config.perturbations["third_bodies"]:
            self.logger.info("Third body perturbations: {third_bodies}".format(**config.perturbations))

        # [NOTE] We want to print all Numpy warnings to stdout, otherwise they are suppressed. However,
        #          some warnings are actually negligible, such as:
        #               "RuntimeWarning: underflow encountered in nextafter"
        #          thrown inside of the `numpy::solve_ivp()` method. Therefore, we don't want to raise, just print.
        seterr(all="warn")

        self._propagate_job_handler = PropagateJobHandler()

        for estimate_number in self.estimate_agents:
            self._propagate_job_handler.registerPropagateCallback(self.estimate_agents[estimate_number].callback)

        for target_agent in self.target_agents.values():
            if isinstance(target_agent.callback, CallbackRegistration):
                self._propagate_job_handler.registerPropagateCallback(target_agent.callback)
            else:
                self._propagate_job_handler.registerImporterCallback(target_agent.simulation_id, target_agent.callback)

        for tasking_engine in self._tasking_engines:
            for simulation_id in tasking_engine.sensor_list:
                callback = self.sensor_agents[simulation_id].callback
                if isinstance(callback, CallbackRegistration):
                    self._propagate_job_handler.registerPropagateCallback(callback)
                else:
                    self._propagate_job_handler.registerImporterCallback(simulation_id, callback)

        self.logger.info("Initialized Scenario.")

    def handleProcessedTask(self, task):
        """Handle completed tasks via the :class:`.QueueManager` process.

        Args:
            task (:class:`.Task`): task object to be handled

        Raises:
            Exception: raised if task-tracking dicts are empty and task is handled
            Exception: raised if task completed in an error state
        """
        if task.status == 'processed':
            if self.execute_tasking_task_ids:
                # process execute estimation updates
                self.execute_tasking_task_ids[task.id].updateFromAsyncUpdateEstimate(
                    task.retval
                )

            else:
                raise Exception("No map to handle task {0.id}.".format(task))

        else:
            raise Exception("Error occurred in task {0.id}:\n\t{0.error}".format(
                task
            ))

    def propagateTo(self, target_time, output_database=None):
        """Propagate the :class:`.Scenario` forward to the given time.

        Args:
            target_time (:class:`.JulianDate`): Julian date of when to propagate to.
            output_database (:class:`.DataInterface`, optional): database to output simulation data
                to. Defaults to ``None``, which means do not output any data.

        Raises:
            ValueError: raised if a `target_time` given is less than :attr:`.ScenarioClock.dt_step`
        """
        target_scenario_time = target_time.convertToScenarioTime(self.clock.julian_date_start)
        rounded_delta = around(target_scenario_time - self.clock.time)

        self.logger.info("Current model time: {0}.".format(
            self.clock.julian_date_epoch,
        ))
        self.logger.info("Target propagation time: {0}. Rounded delta: {1} seconds.".format(
            target_time,
            rounded_delta
        ))

        if rounded_delta >= self.physics_time_step:
            steps = rounded_delta / self.physics_time_step
            self.logger.info("Propagating model forward {0} seconds.".format(
                steps * self.physics_time_step
            ))
            for _ in range(int(steps)):
                self.stepForward()

                # Build the output message on OUTPUT interval timestep
                if self.clock.time % self.output_time_step == 0 and output_database is not None:
                    self.saveDatabaseOutput(output_database)

        else:
            self.logger.error("Delta less than physics time step of {0} seconds.".format(
                self.physics_time_step
            ))
            raise ValueError(rounded_delta)

    def saveDatabaseOutput(self, output_database):
        """Save Truth, Estimate, and Observation data to the output database."""
        # Grab `TruthEphemeris` for targets & sensors
        output_data = [tgt.getCurrentEphemeris() for tgt in self.target_agents.values()]
        output_data.extend(sensor.getCurrentEphemeris() for sensor in self.sensor_network)
        # Grab `EstimateEphemeris` for estimates
        output_data.extend(est.getCurrentEphemeris() for est in self.estimate_agents.values())
        for tasking_engine in self._tasking_engines:
            # Grab `Observations` from current time step
            obs = tasking_engine.getCurrentObservations()
            if obs:
                self.logger.debug(
                    "Saving {0} observations for targets {1} to the database.".format(
                        len(obs),
                        {ob.target_id for ob in obs})
                )
            output_data.extend(obs)
            # Grab tasking data
            output_data.extend(tasking for tasking in tasking_engine.getCurrentTasking(self.current_julian_date))

        # Commit data to output DB
        output_database.bulkSave(output_data)

    def stepForward(self):
        """Propagate the simulation forward by a single timestep."""
        # Call to update the entire model
        self.logger.debug("TicToc")
        self.clock.ticToc()
        self._propagate_job_handler.executeJobs(self.clock)

        # Add truth data to the shared interface
        shared_interface = DataInterface.getSharedInterface()
        ephems = [tgt.getCurrentEphemeris() for tgt in self.target_agents.values()]
        ephems.extend(sensor.getCurrentEphemeris() for sensor in self.sensor_network)
        shared_interface.bulkSave(ephems)

        red = getRedisConnection()
        red.set('sensor_agents', dumps(self.sensor_agents))
        red.set('estimate_agents', dumps(self.estimate_agents))
        red.set('target_agents', dumps(self.target_agents))

        # assess life; quit job; buy motorcycle
        self.logger.debug("Assess")
        obs_dict = defaultdict(list)
        for tasking_engine in self._tasking_engines:
            tasking_engine.assess(self.clock.julian_date_epoch)
            for observation in tasking_engine.cur_step_observations:
                obs_dict[observation.target_id].append(observation)

        # Estimate and covariance are stored as the updated state estimate and covariance
        # If there are no observations, there is no update information and the predicted state
        for estimate in self.estimate_agents:
            task = Task(
                asyncUpdateEstimate,
                args=[
                    self.estimate_agents[estimate],
                    self.target_agents[estimate],
                    obs_dict[estimate]
                ]
            )

            self.execute_tasking_task_ids[task.id] = self.estimate_agents[estimate]
            self.queue_mgr.queueTasks(task)

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

        # Add any nodes as needed
        self.processNodeAdditions()

    def addNode(self, target, tasking_engine):
        """Add a node to the target network.

        Args:
            target (:class:.`NodeAddition`): :class:`.NodeAddition` object representing the node to add.
        """
        # Create new target based on ``NodeAddition``
        initial_state = asarray([
            target.posX, target.posY, target.posZ, target.velX, target.velY, target.velZ
        ])

        # _id, name, initial_state, clock, dynamics, realtime, process_noise, seed=None
        seed = self.scenario_config.noise["random_seed"]
        new_tgt = TargetAgent(
            target.sat_num,
            target.sat_name,
            "Spacecraft",
            initial_state,
            self.clock,
            self._dynamics_method,
            self.scenario_config.propagation["realtime_propagation"],
            self._dynamics_noise_matrix,
            seed=seed
        )

        # Create a filter config object
        filter_config = {
            "filter_type": self.filter.__class__.__name__,
            # Create dynamics object for RSO filter propagation
            "dynamics": self._dynamics_method,
            # Create process noise covariance for uncertainty propagation
            "process_noise": self._filter_noise_matrix,
            "alpha": 0.05,
            "beta": 2.0,
        }

        # Create new ``EstimateAgent`` based on new ``TargetAgent``
        config = {
            "target": new_tgt,
            "init_estimate_error": self.scenario_config.noise["initial_error_magnitude"],
            "rng": default_rng(seed),
            "clock": self.clock,
            "filter": filter_config,
            "seed": seed
        }
        new_est_agent = EstimateAgent.fromConfig(config, events=[])
        self._estimate_agents[new_est_agent.simulation_id] = new_est_agent

        self.target_agents[target.sat_num] = new_tgt
        tasking_engine.target_list[new_tgt.simulation_id] = new_tgt
        tasking_engine.num_targets += 1

    def processNodeAdditions(self):
        """Execute any node additions that are present in the database for the current time."""
        shared_interface = DataInterface.getSharedInterface()
        query = Query([NodeAddition])
        query = addAlmostEqualFilter(query, NodeAddition, 'start_time', float(self.clock.julian_date_epoch))
        node_additions = shared_interface.getData(query)

        for addition in node_additions:
            ## [NOTE]: default to first tasking engine, needs update
            self.addNode(addition, self._tasking_engines[0])
            self.logger.info("Added new target {0}: {1}".format(addition.unique_id, addition.name))

    @staticmethod
    def parseConfigFile(path):
        """Parse out configuration from a given filepath.

        Args:
            path (``str``): path to main config file

        Returns:
            ``dict``: config dictionary object with the necessary fields
        """
        if path.endswith("json"):
            file_loader = loadJSONFile
        elif path.endswith("yaml"):
            file_loader = loadYAMLFile
        else:
            raise ValueError(path)

        # Load the main config, and save the path
        config_file_path = os.path.dirname(os.path.abspath(path))
        configuration = file_loader(path)

        # Load target events
        target_events = None
        target_events_file = configuration.pop("target_event_set", None)
        if target_events_file:
            target_events = file_loader(os.path.join(config_file_path, target_events_file))
        configuration["target_events"] = target_events

        # Load sensor events
        sensor_events = None
        sensor_events_file = configuration.pop("sensor_event_set", None)
        if sensor_events_file:
            sensor_events = file_loader(os.path.join(config_file_path, sensor_events_file))
        configuration["sensor_events"] = sensor_events

        # Load the Tasking Engines
        tasking_engines = configuration.pop("engines")
        configuration["engines"] = []
        for engine in tasking_engines:
            engine_file = file_loader(os.path.join(config_file_path, engine))

            # Load the RSO target set
            target_file = file_loader(os.path.join(config_file_path, engine_file["target_set"]))["targets"]

            # Load the sensor set
            sensor_file = file_loader(os.path.join(config_file_path, engine_file["sensor_set"]))["sensors"]

            configuration["engines"].append({"name": engine,
                                             "targets": target_file,
                                             "sensors": sensor_file,
                                             "reward": engine_file["reward"],
                                             "decision": engine_file["decision"]})

        assert len(configuration["engines"]) > 0, "No engine object included in configuration."

        return configuration

    @classmethod
    def fromConfigFile(cls, path, start_workers=True):
        """Factory to create a :class:`.Scenario` object from a config file.

        Args:
            path (``str``): path to main config file
            start_workers (``bool``, optional): Flag indicating whether this :class:`.Scenario` should
                spin up its own :class:`.WorkerManager` instance or not. Defaults to ``True``.

        Returns:
            :class:`.Scenario`: properly constructed `Scenario` object
        """
        configuration = Scenario.parseConfigFile(path)
        return cls.fromConfig(configuration, start_workers=start_workers)

    @classmethod
    def fromConfig(cls, config, start_workers=True):
        """Factory to create a :class:`.Scenario` object from a config dict.

        Args:
            config (``dict``): configuration dictionary object with the necessary fields
            start_workers (``bool``, optional): Flag indicating whether this :class:`.Scenario` should
                spin up its own :class:`.WorkerManager` instance or not. Defaults to ``True``.

        Returns:
            :class:`.Scenario`: properly constructed `Scenario` object
        """
        # Create :class:`ScenarioBuilder` object, and then instantiate a :class:`.Scenario` object
        builder = ScenarioBuilder(config)
        return cls(
            builder.config,
            builder.clock,
            builder.target_agents,
            builder.estimate_agents,
            builder.sensor_network,
            builder.tasking_engines,
            builder.logger,
            start_workers=start_workers
        )

    @property
    def output_time_step(self):
        """int: returns the configuration output time step in seconds."""
        return self.scenario_config.time["output_step_sec"]

    @property
    def physics_time_step(self):
        """int: returns the configuration physics time step in seconds."""
        return self.scenario_config.time["physics_step_sec"]

    @property
    def julian_date_start(self):
        """int: returns the configuration starting Julian date."""
        return self.clock.julian_date_start

    @property
    def sensor_agents(self):
        """dict: sensor agents indexed by their unique id."""
        return self._sensor_agents

    @property
    def estimate_agents(self):
        """dict: estimate agents indexed by their unique id."""
        return self._estimate_agents
