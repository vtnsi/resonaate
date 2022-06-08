# Standard Library Imports
import logging
import os.path
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
from ..common.logger import Logger
from ..common.utilities import loadJSONFile, loadYAMLFile
from ..data.data_interface import DataInterface
from ..data.node_addition import NodeAddition
from ..data.query_util import addAlmostEqualFilter
from ..dynamics import spacecraftDynamicsFactory
from ..parallel import REDIS_QUEUE_LOGGER
from ..parallel.job_handler import PropagateJobHandler, CallbackRegistration
from ..parallel.worker import WorkerManager
from ..physics.noise import noiseCovarianceFactory


class Scenario:
    """Simulation scenario class for managing .

    The Scenario class is the main simulation object that contains the major simulation pieces. It
    handles stepping the simulation forward, updating the simulation objects, and outputting data.
    This class serves as a "public" API for running RESONAATE simulations.
    """

    def __init__(
            self, config, clock, target_constellation, sensor_network, tasking_engine, logger=None, start_workers=True
    ):
        """Instantiate a Scenario object.

        Args:
            config (:class:`.ScenarioConfig`): configuration used to create this instance, kept for reference.
            clock (:class:`.ScenarioClock`): main clock object for tracking time & managing tasking queues
            target_constellation (:class:`.Constellation`): target RSO constellation for this :class:`.Scenario` .
            sensor_network (:class:`.SOSINetwork`): sensor network for this :class:`.Scenario` .
            tasking_engine (:class:`.TaskingEngine`): tasking engine for this :class:`.Scenario` .
            logger (:class:`.Logger`, optional):pPreviously instantiated :class:`.Logger` instance to be used.
                Defaults to `None`, resulting in the class instantiating its own :class:`.Logger`.
            start_workers (``bool``, optional): Flag indicating whether this :class:`.Scenario` should
                spin up its own :class:`.WorkerManager` instance or not. Defaults to ``True``.
        """
        # Save scenario configuration
        self.scenario_config = config

        # Save the clock object
        self.clock = clock

        # Save target constellation, sensor network, and tasking engine
        self.target_constellation = target_constellation
        self.sensor_network = sensor_network
        self._tasking_engine = tasking_engine

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
        for est_agent in tasking_engine.estimate_list:
            self._propagate_job_handler.registerPropagateCallback(est_agent.callback)

        for tgt_agent in tasking_engine.target_list:
            if isinstance(tgt_agent.callback, CallbackRegistration):
                self._propagate_job_handler.registerPropagateCallback(tgt_agent.callback)
            else:
                self._propagate_job_handler.registerImporterCallback(tgt_agent.simulation_id, tgt_agent.callback)

        for sensor_agent in tasking_engine.sensor_list:
            callback = sensor_agent.callback
            if isinstance(callback, CallbackRegistration):
                self._propagate_job_handler.registerPropagateCallback(callback)
            else:
                self._propagate_job_handler.registerImporterCallback(sensor_agent.simulation_id, callback)

        self.logger.info("Initialized Scenario.")

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
        output_data = [tgt.getCurrentEphemeris() for tgt in self.target_constellation]
        output_data.extend(sensor.getCurrentEphemeris() for sensor in self.sensor_network)
        # Grab `EstimateEphemeris` for estimates
        output_data.extend(est.getCurrentEphemeris() for est in self._tasking_engine.estimate_list)
        # Grab `Observations` from current time step
        obs = self._tasking_engine.getCurrentObservations()
        if obs:
            self.logger.debug(
                "Saving {0} observations for targets {1} to the database.".format(
                    len(obs),
                    {ob.target_id for ob in obs})
            )
        output_data.extend(obs)
        # Grab tasking data
        output_data.extend(tasking for tasking in self._tasking_engine.getCurrentTasking())
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
        ephems = [tgt.getCurrentEphemeris() for tgt in self.target_constellation]
        ephems.extend(sensor.getCurrentEphemeris() for sensor in self.sensor_network)
        shared_interface.bulkSave(ephems)

        # assess life; quit job; buy motorcycle
        self.logger.debug("Assess")
        self._tasking_engine.assess()

        # Add any nodes as needed
        self.processNodeAdditions()

    def addNode(self, target):
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
            "filter_type": "UKF",
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

        self.target_constellation.nodes.append(new_tgt)
        assert len(self._tasking_engine.true_target_list) == len(self.target_constellation.nodes)

        self._tasking_engine.true_target_dict[new_tgt.simulation_id] = new_tgt
        self._tasking_engine.num_targets += 1
        self._tasking_engine.target.append(new_est_agent)

    def processNodeAdditions(self):
        """Execute any node additions that are present in the database for the current time."""
        shared_interface = DataInterface.getSharedInterface()
        query = Query([NodeAddition])
        query = addAlmostEqualFilter(query, NodeAddition, 'start_time', float(self.clock.julian_date_epoch))
        node_additions = shared_interface.getData(query)

        for addition in node_additions:
            self.addNode(addition)
            self.logger.info("Added new target {0}: {1}".format(addition.unique_id, addition.name))

    @classmethod
    def fromConfig(cls, path, start_workers=True):
        """Factory to create a :class:`.Scenario` object from a config file.

        Args:
            path (``str``): path to main config file
            start_workers (``bool``, optional): Flag indicating whether this :class:`.Scenario` should
                spin up its own :class:`.WorkerManager` instance or not. Defaults to ``True``.

        Returns:
            :class:`.Scenario`: properly constructed `Scenario` object
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

        # Load the RSO target set
        target_file = os.path.join(config_file_path, configuration.pop("target_set"))
        configuration.update(file_loader(target_file))

        # Load the sensor set
        sensor_file = os.path.join(config_file_path, configuration.pop("sensor_set"))
        configuration.update(file_loader(sensor_file))

        # Load target events
        target_events = None
        target_events_file = configuration.pop("target_event_set", None)
        if target_events_file:
            target_events = file_loader(os.path.join(config_file_path, target_events_file))
        configuration["target_events"] = target_events

        # Load target events
        sensor_events = None
        sensor_events_file = configuration.pop("sensor_event_set", None)
        if sensor_events_file:
            sensor_events = file_loader(os.path.join(config_file_path, sensor_events_file))
        configuration["sensor_events"] = sensor_events

        # Create :class:`ScenarioBuilder` object, and then instantiate a :class:`.Scenario` object
        builder = ScenarioBuilder(configuration)
        return cls(
            builder.config,
            builder.clock,
            builder.target_constellation,
            builder.sensor_network,
            builder.tasking_engine,
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
