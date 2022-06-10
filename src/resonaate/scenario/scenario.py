"""Defines the :class:`.Scenario` class which controls RESONAATE simulations."""
# Standard Library Imports
import logging
from collections import defaultdict
from functools import singledispatch, update_wrapper
from pickle import dumps

# Third Party Imports
from numpy import around, seterr
from numpy.random import default_rng
from scipy.linalg import norm

# Local Imports
from ..agents.estimate_agent import EstimateAgent
from ..agents.sensing_agent import SensingAgent
from ..agents.target_agent import TargetAgent
from ..common.behavioral_config import BehavioralConfig
from ..common.logger import Logger
from ..data.events import EventScope, getRelevantEvents, handleRelevantEvents
from ..data.resonaate_database import ResonaateDatabase
from ..dynamics import spacecraftDynamicsFactory
from ..dynamics.integration_events.event_stack import EventStack
from ..parallel import REDIS_QUEUE_LOGGER, getRedisConnection, resetMaster
from ..parallel.handlers.agent_propagation import AgentPropagationJobHandler
from ..parallel.handlers.estimate_prediction import EstimatePredictionJobHandler
from ..parallel.handlers.estimate_update import EstimateUpdateJobHandler
from ..parallel.worker import WorkerManager
from ..physics.constants import SEC2DAYS
from ..physics.noise import noiseCovarianceFactory
from ..physics.time.stardate import JulianDate
from .config.agent_configs import SensorConfigObject, TargetConfigObject


def methdispatch(func):
    """Wrap an instance method in the ``singledispatch`` wrapper.

    Args:
        func (callable): Method to be wrapped.

    See Also:
        https://stackoverflow.com/questions/24601722/how-can-i-use-functools-singledispatch-with-instance-methods

    Note:
        This workaround won't be necessary should we upgrade to Python 3.8+.
    """
    dispatcher = singledispatch(func)

    def wrapper(*args, **kw):
        """Wrap method so dispatcher takes second argument, rather than ``self``."""
        return dispatcher.dispatch(args[1].__class__)(*args, **kw)

    wrapper.register = dispatcher.register
    update_wrapper(wrapper, func)
    return wrapper


class Scenario:
    """Simulation scenario class for managing .

    The Scenario class is the main simulation object that contains the major simulation pieces. It
    handles stepping the simulation forward, updating the simulation objects, and outputting data.
    This class serves as a "public" API for running RESONAATE simulations.
    """

    def __init__(
        self,
        config,
        clock,
        target_agents,
        estimate_agents,
        sensor_network,
        tasking_engines,
        estimation_config,
        internal_db_path=None,
        importer_db_path=None,
        logger=None,
        start_workers=True,
    ):
        """Instantiate a Scenario object.

        Args:
            config (:class:`.ScenarioConfig`): configuration used to create this instance, kept for reference.
            clock (:class:`.ScenarioClock`): main clock object for tracking time
            target_agents (``dict``): target RSO objects for this :class:`.Scenario` .
            estimate_agents (``dict``): estimate RSO objects for this :class:`.Scenario` .
            sensor_network (``list``): sensor network for this :class:`.Scenario` .
            tasking_engines (dict): dictionary of tasking engines for this :class:`.Scenario` .
            estimation_config (dict): Dictionary of estimation configuration information.
            internal_db_path (``str``, optional): path to RESONAATE internal database object.
                Defaults to ``None``.
            importer_db_path (``str``, optional): path to external importer database for pre-canned
                data. Defaults to ``None``.
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
        self._sensor_agents = {node.simulation_id: node for node in sensor_network}
        self._tasking_engines = tasking_engines
        self.current_julian_date = self.julian_date_start

        # Save filter configuration
        self.estimation_config = estimation_config

        ## Logging class used to track execution.
        self.logger = logger
        if logger is None:
            self.logger = Logger(
                "resonaate", path=BehavioralConfig.getConfig().logging.OutputLocation
            )

        if BehavioralConfig.getConfig().debugging.ParallelDebugMode:
            self.logger.warning(
                "Simulation is running in debug mode. Worker jobs can block indefinitely."
            )

        REDIS_QUEUE_LOGGER.setLevel(logging.WARNING)
        self.worker_mgr = None
        if start_workers:
            ## Worker manager class instance.
            self.worker_mgr = WorkerManager(daemonic=True)
            self.worker_mgr.startWorkers()

        # Log some basic information about propagation for this simulation
        pos_std = self.scenario_config.noise.init_position_std_km
        vel_std = self.scenario_config.noise.init_velocity_std_km_p_sec
        self.logger.info(f"Initial estimate error std: {pos_std} km; {vel_std} km/sec")
        dynamics_noise = norm(
            noiseCovarianceFactory(
                self.scenario_config.noise.dynamics_noise_type,
                self.scenario_config.time.physics_step_sec,
                self.scenario_config.noise.dynamics_noise_magnitude,
            )
        )
        self.logger.info(f"Dynamics process noise magnitude: {dynamics_noise}")
        self.logger.info(f"Random seed: {config.noise.random_seed}")
        self.logger.info(
            f"Using real-time propagation for RSO truth data: {config.propagation.target_realtime_propagation}"
        )
        self.logger.info(
            f"Using real-time propagation for sensor truth data: {config.propagation.sensor_realtime_propagation}"
        )
        self.logger.info(
            f"Using real-time observation for tasking: {config.propagation.realtime_observation}"
        )
        self.logger.info(
            f"Spacecraft truth dynamics model: {config.propagation.propagation_model}"
        )
        self.logger.info(
            f"Spacecraft filter dynamics model: {config.estimation.sequential_filter.dynamics}"
        )
        self.logger.info(f"Numerical integration method: {config.propagation.integration_method}")
        self.logger.info(f"Earth gravity model: {config.geopotential.model}")
        self.logger.info(
            f"Earth geopotential degree, order: {config.geopotential.degree}, {config.geopotential.order}"
        )
        if config.perturbations.third_bodies:
            self.logger.info(f"Third body perturbations: {config.perturbations.third_bodies}")
        if config.perturbations.solar_radiation_pressure:
            self.logger.info(
                f"Solar Radiation Pressure perturbations: {config.perturbations.solar_radiation_pressure}"
            )
        if config.perturbations.general_relativity:
            self.logger.info(
                f"General Relativity perturbations: {config.perturbations.general_relativity}"
            )

        # [NOTE] We want to print all Numpy warnings to stdout, otherwise they are suppressed. However,
        #          some warnings are actually negligible, such as:
        #               "RuntimeWarning: underflow encountered in nextafter"
        #          thrown inside of the `numpy::solve_ivp()` method. Therefore, we don't want to raise, just print.
        seterr(all="warn")

        # Init database info
        self._importer_db_path = importer_db_path
        self.database = ResonaateDatabase.getSharedInterface(
            db_path=internal_db_path, logger=self.logger
        )

        # Initialize "truth simulation" job queue, and assign callbacks for all target/sensor agents
        self._agent_propagation_handler = AgentPropagationJobHandler(
            importer_db_path=importer_db_path
        )

        for target_agent in self.target_agents.values():
            self._agent_propagation_handler.registerCallback(target_agent)

        for sensor_agent in self.sensor_agents.values():
            self._agent_propagation_handler.registerCallback(sensor_agent)

        # Initialize estimate-related job queues, assign callback for all estimate agents
        self._estimate_update_handler = EstimateUpdateJobHandler()
        self._estimate_update_handler.registerCallback(self)

        self._estimate_prediction_handler = EstimatePredictionJobHandler()
        for estimate_agent in self.estimate_agents.values():
            self._estimate_prediction_handler.registerCallback(estimate_agent)

        # Get the redis connection singleton
        self.redis_conn = getRedisConnection()

        self.logger.info("Initialized Scenario.")

    def propagateTo(self, target_time):
        """Propagate the :class:`.Scenario` forward to the given time.

        Args:
            target_time (:class:`.JulianDate`): Julian date of when to propagate to.

        Raises:
            ValueError: raised if a `target_time` given is less than :attr:`.ScenarioClock.dt_step`
        """
        target_scenario_time = target_time.convertToScenarioTime(self.clock.julian_date_start)
        rounded_delta = around(target_scenario_time - self.clock.time)

        self.logger.info(f"Current model time: {self.clock.julian_date_epoch}.")
        self.logger.info(
            f"Target propagation time: {target_time}. Rounded delta: {rounded_delta} seconds."
        )

        if self.scenario_config.propagation.truth_simulation_only:
            self.logger.info("Truth simulation only - skipping Assess steps")

        if rounded_delta >= self.physics_time_step:
            steps = rounded_delta / self.physics_time_step
            self.logger.info(
                f"Propagating model forward {steps * self.physics_time_step} seconds."
            )
            for _ in range(int(steps)):
                self.stepForward()

                # Build the output message on OUTPUT interval timestep
                if self.clock.time % self.output_time_step == 0:
                    self.saveDatabaseOutput()

        else:
            self.logger.error(
                f"Delta less than physics time step of {self.physics_time_step} seconds."
            )
            raise ValueError(rounded_delta)

    def saveDatabaseOutput(self):
        """Save Truth, Estimate, and Observation data to the output database."""
        # Grab `TruthEphemeris` for targets & sensors
        output_data = [tgt.getCurrentEphemeris() for tgt in self.target_agents.values()]
        output_data.extend(sensor.getCurrentEphemeris() for sensor in self.sensor_agents.values())

        if not self.scenario_config.propagation.truth_simulation_only:
            # Grab `EstimateEphemeris` for estimates
            output_data.extend(est.getCurrentEphemeris() for est in self.estimate_agents.values())
            # Grab `DetectedManeuver`s from the estimate
            detected_maneuvers = set()
            for est in self.estimate_agents.values():
                if est.maneuver_detected:
                    detected_maneuvers.add(est.simulation_id)
                    output_data.extend(est.getDetectedManeuvers())

            if detected_maneuvers:
                msg = f"Committing {len(detected_maneuvers)} maneuver detections of targets {detected_maneuvers}"
                msg += " to the database"
                self.logger.debug(msg)

            # Grab `Observations` from current time step
            for tasking_engine in self._tasking_engines.values():
                obs_tuples = tasking_engine.getCurrentObservations()
                if obs_tuples:
                    msg = f"Committing {len(obs_tuples)} observations of targets "
                    observed_targets = set()
                    for obs_tuple in obs_tuples:
                        observed_targets.add(obs_tuple.observation.target_id)
                    msg += f"{observed_targets} to the database."
                    self.logger.debug(msg)
                output_data.extend(obs_tuple.observation for obs_tuple in obs_tuples)
                # Grab tasking data
                output_data.extend(
                    tasking
                    for tasking in tasking_engine.getCurrentTasking(self.clock.julian_date_epoch)
                )

        # Commit data to output DB
        self.database.bulkSave(output_data)

    def stepForward(self):
        """Propagate the simulation forward by a single timestep."""
        prior_jd = self.current_julian_date
        next_jd = JulianDate(float(prior_jd) + self.clock.dt_step * SEC2DAYS)
        handleRelevantEvents(
            self, self.database, EventScope.SCENARIO_STEP, prior_jd, next_jd, self.logger
        )
        # Call to update the entire model
        self.logger.debug("TicToc")
        # Tic clock forward, push epoch to DB
        self.clock.ticToc()
        # Update Julian date properly
        self.current_julian_date = self.clock.julian_date_epoch

        # Propagate truth model & predict estimate forward in time.
        self._agent_propagation_handler.executeJobs(
            prior_julian_date=prior_jd,
            julian_date=self.clock.julian_date_epoch,
            epoch_time=self.clock.time,
        )

        self.redis_conn.set("target_agents", dumps(self.target_agents))
        self.redis_conn.set("sensor_agents", dumps(self.sensor_agents))
        if not self.scenario_config.propagation.truth_simulation_only:

            self._estimate_prediction_handler.executeJobs(
                prior_julian_date=prior_jd,
                julian_date=self.clock.julian_date_epoch,
                epoch_time=self.clock.time,
            )

            self.redis_conn.set("estimate_agents", dumps(self.estimate_agents))
            # Handle Sensor Time Bias Events
            # [NOTE][parallel-time-bias-event-handling] Step one: query for events and "handle" them.
            sensor_tasking_events = defaultdict(list)
            relevant_events = getRelevantEvents(
                ResonaateDatabase.getSharedInterface(),
                EventScope.OBSERVATION_GENERATION,
                prior_jd,
                self.clock.julian_date_epoch,
            )
            for event in relevant_events:
                sensor_tasking_events[event.scope_instance_id].append(event)
            for sensor_id, sensor_events in sensor_tasking_events.items():
                for event in sensor_events:
                    event.handleEvent(self.sensor_agents[sensor_id])
            # Check to prune time bias events
            for sensor_id in self.sensor_agents:
                self.sensor_agents[sensor_id].pruneTimeBiasEvents()

            # assess life; quit job; buy motorcycle
            self.logger.debug("Assess")
            obs_dict = defaultdict(list)
            for tasking_engine in self._tasking_engines.values():
                tasking_engine.assess(prior_jd, self.clock.julian_date_epoch)
                for obs_tuple in tasking_engine.observations:
                    obs_dict[obs_tuple.observation.target_id].append(obs_tuple)

            # Estimate and covariance are stored as the updated state estimate and covariance
            # If there are no observations, there is no update information and the predicted state
            self._estimate_update_handler.executeJobs(observations=obs_dict)

        # Flush events from event stack
        EventStack.logAndFlushEvents()

    @methdispatch
    def addTarget(self, target_spec, tasking_engine_id):  # pylint: disable=unused-argument
        """Add a target to this :class:`.Scenario`.

        Args:
            target_spec (): Specification of target being added.
            tasking_engine_id (int): Unique identifier to add the specified target to.
        """
        err = f"Can't handle target specification of type {type(target_spec)}"
        raise TypeError(err)

    @addTarget.register(dict)
    def _addTargetDict(self, target_spec, tasking_engine_id):
        """Add a target to this :class:`.Scenario`.

        Args:
            target_spec (dict): Specification of target being added.
            tasking_engine_id (int): Unique identifier to add the specified target to.
        """
        target_conf = TargetConfigObject(target_spec)
        self._addTargetConf(target_conf, tasking_engine_id)

    @addTarget.register(TargetConfigObject)
    def _addTargetConf(self, target_spec, tasking_engine_id):
        """Add a target to this :class:`.Scenario`.

        Args:
            target_spec (TargetConfigObject): Specification of target being added.
            tasking_engine_id (int): Unique identifier to add the specified target to.
        """
        if target_spec.sat_num in self.target_agents:
            err = f"Target '{target_spec.sat_num} already exists in this scenario."
            raise Exception(err)

        target_dynamics = spacecraftDynamicsFactory(
            self.scenario_config.propagation.propagation_model,
            self.clock,
            self.scenario_config.geopotential,
            self.scenario_config.perturbations,
            method=self.scenario_config.propagation.integration_method,
        )

        dynamics_noise = noiseCovarianceFactory(
            self.scenario_config.noise.dynamics_noise_type,
            self.scenario_config.time.physics_step_sec,
            self.scenario_config.noise.dynamics_noise_magnitude,
        )

        filter_dynamics = spacecraftDynamicsFactory(
            self.scenario_config.propagation.propagation_model,
            self.clock,
            self.scenario_config.geopotential,
            self.scenario_config.perturbations,
            method=self.scenario_config.propagation.integration_method,
        )

        filter_noise = noiseCovarianceFactory(
            self.scenario_config.noise.filter_noise_type,
            self.scenario_config.time.physics_step_sec,
            self.scenario_config.noise.filter_noise_magnitude,
        )

        target_factory_config = {
            "target": target_spec,
            "clock": self.clock,
            "dynamics": target_dynamics,
            "realtime": self.scenario_config.propagation.target_realtime_propagation,
            "station_keeping": target_spec.station_keeping,
            "noise": dynamics_noise,
            "random_seed": self.scenario_config.noise.random_seed,
        }
        target_agent = TargetAgent.fromConfig(target_factory_config, events=[])
        self.target_agents[target_spec.sat_num] = target_agent

        estimate_factory_config = {
            "target": target_agent,
            "position_std": self.scenario_config.noise.init_position_std_km,
            "velocity_std": self.scenario_config.noise.init_velocity_std_km_p_sec,
            "rng": default_rng(self.scenario_config.noise.random_seed),
            "clock": self.clock,
            "sequential_filter": self.scenario_config.estimation.sequential_filter,
            "adaptive_filter": self.scenario_config.estimation.adaptive_filter,
            "seed": self.scenario_config.noise.random_seed,
            "dynamics": filter_dynamics,
            "q_matrix": filter_noise,
        }
        estimate_agent = EstimateAgent.fromConfig(estimate_factory_config, events=[])
        self._estimate_agents[target_spec.sat_num] = estimate_agent

        self._tasking_engines[tasking_engine_id].addTarget(target_agent.simulation_id)
        self._agent_propagation_handler.registerCallback(target_agent)
        self._estimate_prediction_handler.registerCallback(estimate_agent)

    def removeTarget(self, agent_id, tasking_engine_id):
        """Remove a target from this :class:`.Scenario`.

        Args:
            agent_id (int): Unique identifier of target being removed.
            tasking_engine_id (int): Unique identifier of tasking engine target is being removed from.
        """
        if agent_id not in self.target_agents:
            err = f"Target '{agent_id} doesn't exist in this scenario."
            raise Exception(err)

        self._agent_propagation_handler.deregisterCallback(agent_id)
        del self.target_agents[agent_id]
        self._estimate_prediction_handler.deregisterCallback(agent_id)
        del self._estimate_agents[agent_id]
        self._tasking_engines[tasking_engine_id].removeTarget(agent_id)

    @methdispatch
    def addSensor(self, sensor_spec, tasking_engine_id):  # pylint: disable=unused-argument
        """Add a sensor to this :class:`.Scenario`.

        Args:
            sensor_spec (): Specification of sensor being added.
            tasking_engine_id (int): Unique identifier to add the specified sensor to.
        """
        err = f"Can't handle sensor specification of type {type(sensor_spec)}"
        raise TypeError(err)

    @addSensor.register(dict)
    def _addSensorDict(self, sensor_spec, tasking_engine_id):
        """Add a sensor to this :class:`.Scenario`.

        Args:
            sensor_spec (dict): Specification of sensor being added.
            tasking_engine_id (int): Unique identifier to add the specified sensor to.
        """
        sensor_conf = SensorConfigObject(sensor_spec)
        self._addSensorConf(sensor_conf, tasking_engine_id)

    @addSensor.register(SensorConfigObject)
    def _addSensorConf(self, sensor_spec, tasking_engine_id):
        """Add a sensor to this :class:`.Scenario`.

        Args:
            sensor_spec (SensorConfigObject): Specification of sensor being added.
            tasking_engine_id (int): Unique identifier to add the specified sensor to.
        """
        if sensor_spec.id in self._sensor_agents:
            err = f"Sensor '{sensor_spec.id} already exists in this scenario."
            raise Exception(err)

        dynamics_method = spacecraftDynamicsFactory(
            self.scenario_config.propagation.propagation_model,
            self.clock,
            self.scenario_config.geopotential,
            self.scenario_config.perturbations,
            method=self.scenario_config.propagation.integration_method,
        )

        config = {
            "agent": sensor_spec,
            "clock": self.clock,
            "satellite_dynamics": dynamics_method,
            "realtime": self.scenario_config.propagation.sensor_realtime_propagation,
            "field_of_view_calculation": self.scenario_config.observation.field_of_view,
        }

        sensing_agent = SensingAgent.fromConfig(config, events=[])
        self._sensor_agents[sensing_agent.simulation_id] = sensing_agent

        self._tasking_engines[tasking_engine_id].addSensor(sensing_agent.simulation_id)
        self._agent_propagation_handler.registerCallback(sensing_agent)

    def removeSensor(self, agent_id, tasking_engine_id):
        """Remove a sensor from this :class:`.Scenario`.

        Args:
            agent_id (int): Unique identifier of sensor being removed.
            tasking_engine_id (int): Unique identifier of tasking engine sensor is being removed from.
        """
        if agent_id not in self._sensor_agents:
            err = f"Sensor '{agent_id} doesn't exist in this scenario."
            raise Exception(err)

        del self.sensor_agents[agent_id]
        self._tasking_engines[tasking_engine_id].removeSensor(agent_id)

    @property
    def output_time_step(self):
        """int: returns the configuration output time step in seconds."""
        return self.scenario_config.time.output_step_sec

    @property
    def physics_time_step(self):
        """int: returns the configuration physics time step in seconds."""
        return self.scenario_config.time.physics_step_sec

    @property
    def julian_date_start(self):
        """int: returns the configuration starting Julian date."""
        return self.clock.julian_date_start

    @property
    def tasking_engines(self):
        """dict: tasking engines indexed by their unique id."""
        return self._tasking_engines

    @property
    def sensor_agents(self):
        """dict: sensor agents indexed by their unique id."""
        return self._sensor_agents

    @property
    def estimate_agents(self):
        """dict: estimate agents indexed by their unique id."""
        return self._estimate_agents

    def shutdown(self, flushall=True):
        """Gracefully shuts down the simulation.

        Make sure Redis 'master' variable gets reset and workers are shut down nicely.

        Args:
            flushall (``bool``, optional): whether to flush the Redis keys on shutdown. Defaults to True.
        """
        if self.worker_mgr:
            self.worker_mgr.stopWorkers(no_wait=True)

        if flushall:
            self.redis_conn.flushall(asynchronous=True)

        resetMaster(self.redis_conn)
        self.redis_conn.close()

    def __del__(self):
        """Gracefully shutdown if simulation goes out of scope.

        See Also:
            :class:`~.Scenario.shutdown`
        """
        self.shutdown(flushall=True)
