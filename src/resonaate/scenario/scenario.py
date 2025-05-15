"""Defines the :class:`.Scenario` class which controls RESONAATE simulations."""

from __future__ import annotations

# Standard Library Imports
from collections import defaultdict
from copy import deepcopy
from functools import singledispatchmethod
from typing import TYPE_CHECKING

# Third Party Imports
import ray
from numpy import around, seterr
from sqlalchemy.orm import Query

# Local Imports
from ..agents.estimate_agent import EstimateAgent
from ..agents.sensing_agent import SensingAgent
from ..agents.target_agent import TargetAgent
from ..common import pathSafeTime
from ..common.behavioral_config import BehavioralConfig
from ..common.logger import Logger
from ..data import getDBConnection
from ..data.epoch import Epoch
from ..data.events import EventScope, getRelevantEvents, handleRelevantEvents
from ..dynamics import dynamicsFactory
from ..dynamics.importer import EphemerisImporter
from ..dynamics.integration_events.event_stack import EventStack
from ..estimation.debug_utils import checkThreeSigmaObservation
from ..parallel.agent_propagation import PropagateExecutor, PropagateRegistration
from ..parallel.estimate_prediction import EstPredictExecutor, EstPredictRegistration
from ..parallel.estimate_update import EstUpdateExecutor, EstUpdateRegistration
from ..physics.constants import SEC2DAYS
from ..physics.time.stardate import JulianDate
from .config.agent_config import AgentConfig, SensingAgentConfig

# Type Checking Imports
if TYPE_CHECKING:
    # Standard Library Imports

    # Local Imports
    from ..data.observation import MissedObservation, Observation
    from ..physics.time.stardate import ScenarioTime
    from ..tasking.engine.engine_base import TaskingEngine
    from .clock import ScenarioClock
    from .config import ScenarioConfig


class AgentAdditionError(Exception):
    """Agent with the same ID already exists in the simulation."""


class AgentRemovalError(Exception):
    """Agent with the ID doesn't exist in the simulation."""


class Scenario:
    """Simulation scenario class for managing .

    The Scenario class is the main simulation object that contains the major simulation pieces. It
    handles stepping the simulation forward, updating the simulation objects, and outputting data.
    This class serves as a "public" API for running RESONAATE simulations.
    """

    def __init__(
        self,
        config: ScenarioConfig,
        clock: ScenarioClock,
        target_agents: dict[int, TargetAgent],
        estimate_agents: dict[int, EstimateAgent],
        sensor_agents: dict[int, SensingAgent],
        tasking_engines: dict[int, TaskingEngine],
        importer_db_path: str | None = None,
        logger: Logger | None = None,
    ):
        """Instantiate a Scenario object.

        Args:
            config (:class:`.ScenarioConfig`): configuration used to create this instance, kept for reference.
            clock (:class:`.ScenarioClock`): main clock object for tracking time
            target_agents (``dict``): target RSO objects for this :class:`.Scenario` .
            estimate_agents (``dict``): estimate RSO objects for this :class:`.Scenario` .
            sensor_agents (``dict``): sensor network for this :class:`.Scenario` .
            tasking_engines (``dict``): dictionary of tasking engines for this :class:`.Scenario` .
            importer_db_path (``str``, optional): path to external importer database for pre-canned
                data. Defaults to ``None``.
            logger (:class:`.Logger`, optional):pPreviously instantiated :class:`.Logger` instance to be used.
                Defaults to `None`, resulting in the class instantiating its own :class:`.Logger`.
        """
        # Save scenario configuration
        self.scenario_config = config

        # Save the clock object
        self.clock = clock

        # Save target_agents, estimate_agents, sensor network, tasking engine and filter
        self.target_agents = target_agents
        self._estimate_agents = estimate_agents
        self._sensor_agents = sensor_agents
        self._tasking_engines = tasking_engines
        self.current_julian_date = self.julian_date_start

        # Save filter configuration
        self.estimation_config = config.estimation

        ## Logging class used to track execution.
        self.logger = logger
        if logger is None:
            self.logger = Logger(
                "resonaate",
                path=BehavioralConfig.getConfig().logging.OutputLocation,
            )

        # Log some basic information about propagation for this simulation
        pos_std = self.scenario_config.noise.init_position_std_km
        vel_std = self.scenario_config.noise.init_velocity_std_km_p_sec
        self.logger.info(f"Initial estimate error std: {pos_std} km; {vel_std} km/sec")
        self.logger.info(f"Random seed: {config.noise.random_seed}")
        self.logger.info(
            f"Using real-time propagation for RSO truth data: {config.propagation.target_realtime_propagation}",
        )
        self.logger.info(
            f"Using real-time propagation for sensor truth data: {config.propagation.sensor_realtime_propagation}",
        )
        self.logger.info(
            f"Using real-time observation for tasking: {config.observation.realtime_observation}",
        )
        self.logger.info(
            f"Spacecraft truth dynamics model: {config.propagation.propagation_model}",
        )
        self.logger.info(
            f"Spacecraft filter dynamics model: {config.estimation.sequential_filter.dynamics_model}",
        )
        self.logger.info(f"Numerical integration method: {config.propagation.integration_method}")
        self.logger.info(f"Earth gravity model: {config.geopotential.model}")
        self.logger.info(
            f"Earth geopotential degree, order: {config.geopotential.degree}, {config.geopotential.order}",
        )
        if config.perturbations.third_bodies:
            self.logger.info(f"Third body perturbations: {config.perturbations.third_bodies}")
        if config.perturbations.solar_radiation_pressure:
            self.logger.info(
                f"Solar Radiation Pressure perturbations: {config.perturbations.solar_radiation_pressure}",
            )
        if config.perturbations.general_relativity:
            self.logger.info(
                f"General Relativity perturbations: {config.perturbations.general_relativity}",
            )

        # [NOTE] We want to print all Numpy warnings to stdout, otherwise they are suppressed. However,
        #          some warnings are actually negligible, such as:
        #               "RuntimeWarning: underflow encountered in nextafter"
        #          thrown inside of the `numpy::solve_ivp()` method. Therefore, we don't want to raise, just print.
        seterr(all="warn")

        # Init database info
        self._importer_db_path = importer_db_path
        self._ephem_importer = None
        if not (
            config.propagation.target_realtime_propagation
            and config.propagation.sensor_realtime_propagation
        ):
            self._ephem_importer = EphemerisImporter(self._importer_db_path)
        self.database = getDBConnection()

        # Initialize "truth simulation" job queue, and assign callbacks for all target/sensor agents
        self._agent_propagator = PropagateExecutor()

        self._estimate_updater = EstUpdateExecutor()
        self._estimate_predictor = EstPredictExecutor()

        self._target_store = {}
        self._sensor_store = {}
        self._estimate_store = {}

        # Save initial states to database
        self.saveDatabaseOutput()

        self.logger.info("Initialized Scenario.")

    def propagateTo(self, target_time: JulianDate) -> None:
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
            f"Target propagation time: {target_time}. Rounded delta: {rounded_delta} seconds.",
        )

        if self.scenario_config.propagation.truth_simulation_only:
            self.logger.info("Truth simulation only - skipping Assess steps")

        if rounded_delta >= self.physics_time_step:
            steps = rounded_delta / self.physics_time_step
            self.logger.info(
                f"Propagating model forward {steps * self.physics_time_step} seconds.",
            )
            for _ in range(int(steps)):
                self.stepForward()

                # Build the output message on OUTPUT interval timestep
                if self.clock.time % self.output_time_step == 0:
                    self.saveDatabaseOutput()

        else:
            self.logger.error(
                f"Delta less than physics time step of {self.physics_time_step} seconds.",
            )
            raise ValueError(rounded_delta)

    def saveDatabaseOutput(self) -> None:  # noqa: C901
        """Save Truth, Estimate, and Observation data to the output database."""
        # Grab `TruthEphemeris` for targets & sensors
        if not self.database.getData(
            Query(Epoch).filter(
                Epoch.timestampISO == self.clock.datetime_epoch.isoformat(timespec="microseconds"),
            ),
            multi=False,
        ):
            self.database.insertData(
                Epoch(
                    julian_date=self.clock.julian_date_epoch,
                    timestampISO=self.clock.datetime_epoch.isoformat(timespec="microseconds"),
                ),
            )

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
                # Save Successful Observations
                if observations := tasking_engine.getCurrentObservations():
                    self._logObservations(observations)
                output_data.extend(observations)

                # Save Missed Observations
                if missed_observations := tasking_engine.getCurrentMissedObservations():
                    self._logMissedObservations(missed_observations)
                output_data.extend(missed_observations)
                # Grab tasking data
                output_data.extend(
                    tasking
                    for tasking in tasking_engine.getCurrentTasking(self.clock.julian_date_epoch)
                )

        if self.estimation_config.sequential_filter.save_filter_steps:
            # Obtain all filter steps and save them to the db.
            agents: list[EstimateAgent] = [
                self.estimate_agents[key] for key in self.estimate_agents
            ]
            for agent in agents:
                agent_filters = agent.getFilterSteps()
                output_data.extend(filter_step for filter_step in agent_filters)

        # Commit data to output DB
        self.database.bulkSave(output_data)

    def stepForward(self) -> None:  # noqa: C901, PLR0912
        """Propagate the simulation forward by a single timestep."""
        prior_jd = self.current_julian_date
        prior_datetime = self.clock.datetime_epoch
        next_jd = JulianDate(float(prior_jd) + self.clock.dt_step * SEC2DAYS)
        handleRelevantEvents(
            self,
            self.database,
            EventScope.SCENARIO_STEP,
            prior_jd,
            next_jd,
            self.logger,
        )

        # [NOTE][parallel-maneuver-event-handling] Step one: query for events and "handle" them.
        relevant_events = getRelevantEvents(
            self.database,
            EventScope.AGENT_PROPAGATION,
            prior_jd,
            next_jd,
        )
        for event in relevant_events:
            event.handleEvent(self.target_agents[event.scope_instance_id])
            if event.planned:
                event.handleEvent(self.estimate_agents[event.scope_instance_id])

        # Call to update the entire model
        self.logger.debug("TicToc")
        # Tic clock forward, push epoch to DB
        self.clock.ticToc()
        # Update Julian date properly
        self.current_julian_date = self.clock.julian_date_epoch

        # Propagate truth model & predict estimate forward in time.
        for target_agent in self.target_agents.values():
            if target_agent.realtime:
                self._agent_propagator.enqueueJob(PropagateRegistration(target_agent))
            elif self._ephem_importer is not None:
                self._ephem_importer.registerAgent(target_agent)
            else:
                err = f"Agent {target_agent.simulation_id} configured for imported ephemeris, but no importer database was provided."
                self.logger.error(err)
                raise RuntimeError(err)
        for sensor_agent in self.sensor_agents.values():
            if sensor_agent.realtime:
                self._agent_propagator.enqueueJob(PropagateRegistration(sensor_agent))
            elif self._ephem_importer is not None:
                self._ephem_importer.registerAgent(sensor_agent)
            else:
                err = f"Agent {sensor_agent.simulation_id} configured for imported ephemeris, but no importer database was provided."
                self.logger.error(err)
                raise RuntimeError(err)
        if self._ephem_importer is not None:
            self._ephem_importer.importEphemerides(self.clock.datetime_epoch)
        self._agent_propagator.join()

        if not self.scenario_config.propagation.truth_simulation_only:
            self.logger.debug("Predict estimates...")
            for estimate_agent in self.estimate_agents.values():
                self._estimate_predictor.enqueueJob(EstPredictRegistration(estimate_agent))
            self._estimate_predictor.join()

            # Handle Sensor Time Bias Events
            # [NOTE][parallel-time-bias-event-handling] Step one: query for events and "handle" them.
            relevant_events = getRelevantEvents(
                self.database,
                EventScope.OBSERVATION_GENERATION,
                prior_jd,
                self.clock.julian_date_epoch,
            )
            for event in relevant_events:
                event.handleEvent(self.sensor_agents[event.scope_instance_id])

            self.logger.debug("Put agent updates...")
            for target_id, target in self.target_agents.items():
                self._target_store[target_id] = ray.put(target)
            for sensor_id, sensor in self.sensor_agents.items():
                sensor.pruneTimeBiasEvents()
                self._sensor_store[sensor_id] = ray.put(sensor)
            for estimate_id, estimate in self.estimate_agents.items():
                self._estimate_store[estimate_id] = ray.put(estimate)

            # assess life; quit job; buy motorcycle
            self.logger.debug("Assess")
            obs_dict = defaultdict(list)
            for tasking_engine in self._tasking_engines.values():
                tasking_engine.setHandles(
                    self._target_store,
                    self._sensor_store,
                    self._estimate_store,
                )
                tasking_engine.assess(prior_datetime, self.clock.datetime_epoch)

                # Update sensor boresight, and last time that it made an observation
                for sensor_change in tasking_engine.sensor_changes:
                    self.sensor_agents[sensor_change].updateInfo(
                        tasking_engine.sensor_changes[sensor_change],
                    )
                for observation in tasking_engine.observations:
                    if BehavioralConfig.getConfig().debugging.ThreeSigmaObs:
                        debug_output = checkThreeSigmaObservation(
                            self.sensor_agents[observation.sensor_id],
                            self.target_agents[observation.target_id],
                            observation,
                        )
                        if debug_output:
                            msg = f"Collected bad observation: {debug_output}"
                            self.logger.warning(msg)

                    obs_dict[observation.target_id].append(observation)

                tasking_engine.resetHandles()

            # Estimate and covariance are stored as the updated state estimate and covariance
            # If there are no observations, there is no update information and the predicted state
            self.logger.debug("Updating estimate agents...")
            for estimate_agent in self.estimate_agents.values():
                self._estimate_updater.enqueueJob(
                    EstUpdateRegistration(
                        estimate_agent,
                        self._estimate_store[estimate_agent.simulation_id],
                        obs_dict[estimate_agent.simulation_id],
                    ),
                )
            self._estimate_updater.join()

            self._target_store = {}
            self._sensor_store = {}
            self._estimate_store = {}

        # Flush events from event stack
        EventStack.logAndFlushEvents()

    def _logObservations(self, observations: list[Observation]):
        """Log :class:`.Observation` objects."""
        msg = f"Committing {len(observations)} observations of targets "
        observed_targets = set()
        for observation in observations:
            observed_targets.add(observation.target_id)
        msg += f"{observed_targets} to the database."
        self.logger.debug(msg)

    def _logMissedObservations(self, missed_observations: list[MissedObservation]):
        """Log :class:`.MissedObservation` objects."""
        msg = "Missed Observations of targets "
        missed_targets = set()
        for miss in missed_observations:
            missed_targets.add(miss.target_id)
        msg += f"{missed_targets}"
        self.logger.debug(msg)

    @singledispatchmethod
    def addTarget(self, target_spec: AgentConfig | dict, tasking_engine_id: int) -> None:
        """Add a target to this :class:`.Scenario`.

        Args:
            target_spec (:class:`.AgentConfig` | ``dict``): Specification of target being added.
            tasking_engine_id (``int``): Unique identifier to add the specified target to.
        """
        err = f"Can't handle target specification of type {type(target_spec)}"
        raise TypeError(err)

    @addTarget.register
    def _addTargetDict(self, target_spec: dict, tasking_engine_id: int) -> None:
        """Add a target to this :class:`.Scenario`.

        Args:
            target_spec (``dict``): Specification of target being added.
            tasking_engine_id (``int``): Unique identifier to add the specified target to.
        """
        target_conf = AgentConfig(**target_spec)
        self._addTargetConf(target_conf, tasking_engine_id)

    @addTarget.register
    def _addTargetConf(self, target_spec: AgentConfig, tasking_engine_id: int) -> None:
        """Add a target to this :class:`.Scenario`.

        Args:
            target_spec (:class:`.AgentConfig`): Specification of target being added.
            tasking_engine_id (``int``): Unique identifier to add the specified target to.
        """
        if target_spec.id in self.target_agents:
            err = f"Target '{target_spec.id} already exists in this scenario."
            raise AgentAdditionError(err)

        target_dynamics = dynamicsFactory(
            target_spec,
            self.scenario_config.propagation,
            self.scenario_config.geopotential,
            self.scenario_config.perturbations,
            self.clock,
        )

        est_prop_cfg = deepcopy(self.scenario_config.propagation)
        est_prop_cfg.propagation_model = (
            self.scenario_config.estimation.sequential_filter.dynamics_model
        )
        filter_dynamics = dynamicsFactory(
            target_spec,
            est_prop_cfg,
            self.scenario_config.geopotential,
            self.scenario_config.perturbations,
            self.clock,
        )

        target_agent = TargetAgent.fromConfig(
            tgt_cfg=target_spec,
            clock=self.clock,
            dynamics=target_dynamics,
            prop_cfg=self.scenario_config.propagation,
        )
        self.target_agents[target_spec.id] = target_agent

        estimate_agent = EstimateAgent.fromConfig(
            tgt_cfg=target_spec,
            clock=self.clock,
            dynamics=filter_dynamics,
            time_cfg=self.scenario_config.time,
            noise_cfg=self.scenario_config.noise,
            estimation_cfg=self.scenario_config.estimation,
        )
        self._estimate_agents[target_spec.id] = estimate_agent

        self._tasking_engines[tasking_engine_id].addTarget(target_agent.simulation_id)

    def removeTarget(self, agent_id: int, tasking_engine_id: int) -> None:
        """Remove a target from this :class:`.Scenario`.

        Args:
            agent_id (``int``): Unique identifier of target being removed.
            tasking_engine_id (``int``): Unique identifier of tasking engine target is being removed from.
        """
        if agent_id not in self.target_agents:
            err = f"Target '{agent_id} doesn't exist in this scenario."
            raise AgentRemovalError(err)

        del self.target_agents[agent_id]
        del self._estimate_agents[agent_id]
        self._tasking_engines[tasking_engine_id].removeTarget(agent_id)

    @singledispatchmethod
    def addSensor(self, sensor_spec: SensingAgentConfig | dict, tasking_engine_id: int) -> None:
        """Add a sensor to this :class:`.Scenario`.

        Args:
            sensor_spec (:class:`.SensingAgentConfig` | ``dict``): Specification of sensor being added.
            tasking_engine_id (``int``): Unique identifier to add the specified sensor to.
        """
        err = f"Can't handle sensor specification of type {type(sensor_spec)}"
        raise TypeError(err)

    @addSensor.register
    def _addSensorDict(self, sensor_spec: dict, tasking_engine_id: int) -> None:
        """Add a sensor to this :class:`.Scenario`.

        Args:
            sensor_spec (``dict``): Specification of sensor being added.
            tasking_engine_id (``int``): Unique identifier to add the specified sensor to.
        """
        sensor_conf = SensingAgentConfig(**sensor_spec)
        self._addSensorConf(sensor_conf, tasking_engine_id)

    @addSensor.register
    def _addSensorConf(self, sensor_spec: SensingAgentConfig, tasking_engine_id: int) -> None:
        """Add a sensor to this :class:`.Scenario`.

        Args:
            sensor_spec (:class:`.SensingAgentConfig`): Specification of sensor being added.
            tasking_engine_id (``int``): Unique identifier to add the specified sensor to.
        """
        if sensor_spec.id in self._sensor_agents:
            err = f"Sensor '{sensor_spec.id} already exists in this scenario."
            raise AgentAdditionError(err)

        dynamics = dynamicsFactory(
            sensor_spec,
            self.scenario_config.propagation,
            self.scenario_config.geopotential,
            self.scenario_config.perturbations,
            self.clock,
        )

        sensing_agent = SensingAgent.fromConfig(
            sen_cfg=sensor_spec,
            clock=self.clock,
            dynamics=dynamics,
            prop_cfg=self.scenario_config.propagation,
        )
        self._sensor_agents[sensing_agent.simulation_id] = sensing_agent

        self._tasking_engines[tasking_engine_id].addSensor(sensing_agent.simulation_id)

    def removeSensor(self, agent_id: int, tasking_engine_id: int) -> None:
        """Remove a sensor from this :class:`.Scenario`.

        Args:
            agent_id (``int``): Unique identifier of sensor being removed.
            tasking_engine_id (``int``): Unique identifier of tasking engine sensor is being removed from.
        """
        if agent_id not in self._sensor_agents:
            err = f"Sensor '{agent_id} doesn't exist in this scenario."
            raise AgentRemovalError(err)

        del self.sensor_agents[agent_id]
        self._tasking_engines[tasking_engine_id].removeSensor(agent_id)

    @property
    def output_time_step(self) -> ScenarioTime:
        """`:class:`.ScenarioTime`: returns the configuration output time step in seconds."""
        return self.scenario_config.time.output_step_sec

    @property
    def physics_time_step(self) -> ScenarioTime:
        """`:class:`.ScenarioTime`: returns the configuration physics time step in seconds."""
        return self.scenario_config.time.physics_step_sec

    @property
    def julian_date_start(self) -> JulianDate:
        """`:class:`.JulianDate`: returns the configuration starting Julian date."""
        return self.clock.julian_date_start

    @property
    def tasking_engines(self) -> dict[int, TaskingEngine]:
        """``dict``: tasking engines indexed by their unique id."""
        return self._tasking_engines

    @property
    def sensor_agents(self) -> dict[int, SensingAgent]:
        """``dict``: sensor agents indexed by their unique id."""
        return self._sensor_agents

    @property
    def estimate_agents(self) -> dict[int, EstimateAgent]:
        """``dict``: estimate agents indexed by their unique id."""
        return self._estimate_agents

    def shutdown(self) -> None:
        """Record `ray` profiling timeline for performance analysis."""
        ray.timeline(f"timeline_{pathSafeTime()}.json")
        ray.shutdown()
