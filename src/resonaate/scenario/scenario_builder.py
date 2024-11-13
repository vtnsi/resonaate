"""Defines the :class:`.ScenarioBuilder` class to build valid :class:`.Scenario` objects from given configurations."""

from __future__ import annotations

# Standard Library Imports
from copy import deepcopy
from typing import TYPE_CHECKING

# Local Imports
from ..agents.estimate_agent import EstimateAgent
from ..agents.sensing_agent import SensingAgent
from ..agents.target_agent import TargetAgent
from ..common.behavioral_config import BehavioralConfig
from ..common.exceptions import DuplicateEngineError, DuplicateSensorError, DuplicateTargetError
from ..common.logger import Logger
from ..data import getDBConnection
from ..data.agent import AgentModel
from ..data.events import Event
from ..dynamics import dynamicsFactory
from ..tasking.decisions import decisionFactory
from ..tasking.engine.centralized_engine import CentralizedTaskingEngine
from ..tasking.rewards import rewardsFactory
from .clock import ScenarioClock
from .config.event_configs import MissingDataDependencyError

# Type Checking Imports
if TYPE_CHECKING:
    # Standard Library Imports
    from pathlib import Path

    # Local Imports
    from ..data.resonaate_database import ResonaateDatabase
    from ..tasking.engine.engine_base import TaskingEngine
    from .config import AgentConfig, EngineConfig, ScenarioConfig, SensingAgentConfig


class ScenarioBuilder:
    """Builder pattern to create a :class:`.Scenario` object from a configuration dict.

    This contains the requisite logic to properly build all the supplementary objects required to
    properly construct a :class:`.Scenario` object.
    """

    def __init__(
        self,
        scenario_config: ScenarioConfig,
        importer_db_path: str | None = None,
    ) -> None:
        """Instantiate a :class:`.ScenarioBuilder` from a config dictionary.

        Args:
            scenario_config (:class:`.ScenarioConfig`): config settings to make a valid :class:`.Scenario`
            importer_db_path (``str``, optional): path to external importer database for pre-canned
                data. Defaults to ``None``.

        Raises:
            ValueError: raised if the "engines" field is empty
        """
        # Create logger from configs
        self.logger = Logger("resonaate", path=BehavioralConfig.getConfig().logging.OutputLocation)
        # Save base config
        self._config = scenario_config

        # Instantiate clock based on config's start time and class variables
        self.clock = ScenarioClock.fromConfig(self.config.time)

        self.validated_target_configs: dict[int, AgentConfig] = {}
        self.validated_sensor_configs: dict[int, SensingAgentConfig] = {}

        self.tasking_engines = self._initTaskingEngines(importer_db_path=importer_db_path)
        self.target_agents = self._initTargets()
        self.estimate_agents = self._initEstimates()
        self.sensor_agents = self._initSensors()

        # Store agent data in the database FIRST for events that rely on them
        shared_database = getDBConnection()
        self._loadAgentsIntoDatabase(shared_database)
        self._loadEventsIntoDatabase(shared_database)

    def _initTaskingEngines(self, importer_db_path: str | Path) -> dict[int, TaskingEngine]:
        """Initialize targets based on configs.

        Args:
            importer_db_path (``str | Path``): qualified path to importer database.

        Returns:
            ``dict``: constructed :class:`.TaskingEngine` objects
        """
        tasking_engines: dict[int, TaskingEngine] = {}
        engine_conf: EngineConfig
        for engine_conf in self._config.engines:
            if engine_conf.unique_id in tasking_engines:
                err = f"Engines share a unique ID: {engine_conf.unique_id}"
                raise DuplicateEngineError(err)

            # Create Reward & Decision from configuration
            reward = rewardsFactory(engine_conf.reward)
            self.logger.info(f"Reward function: {reward.__class__.__name__}")
            decision = decisionFactory(engine_conf.decision)
            self.logger.info(f"Decision function: {decision.__class__.__name__}")

            # Build target and sensing agent sets
            engine_targets = self._validateTargetAgents(engine_conf)
            engine_sensors = self._validateSensingAgents(engine_conf)

            # Create the tasking engine object
            tasking_engine = CentralizedTaskingEngine(
                engine_conf.unique_id,
                engine_sensors,
                engine_targets,
                reward,
                decision,
                importer_db_path,
                self.config.observation.realtime_observation,
            )

            tasking_engines[tasking_engine.unique_id] = tasking_engine
            self.logger.info(
                f"Successfully built tasking engine: {tasking_engine.__class__.__name__}",
            )

        self.logger.info(f"Successfully loaded {len(tasking_engines)} tasking engines")
        return tasking_engines

    def _initTargets(self) -> dict[int, TargetAgent]:
        """Initialize targets based on a given config.

        Returns:
            ``dict``: constructed :class:`.TargetAgent` objects for each specified agent
        """
        target_agents: dict[int, TargetAgent] = {}
        for target_cfg in self.validated_target_configs.values():
            dynamics = dynamicsFactory(
                target_cfg,
                self.config.propagation,
                self.config.geopotential,
                self.config.perturbations,
                self.clock,
            )

            target_agents[target_cfg.id] = TargetAgent.fromConfig(
                tgt_cfg=target_cfg,
                clock=self.clock,
                dynamics=dynamics,
                prop_cfg=self.config.propagation,
            )

        self.logger.info(f"Successfully loaded {len(target_agents)} target agents")
        return target_agents

    def _initEstimates(self) -> dict[int, EstimateAgent]:
        """Initialize estimates based on a given config.

        Returns:
            ``dict``: constructed :class:`.EstimateAgent` objects for each specified agent
        """
        # Copy propagation model from regular dynamics
        est_prop_cfg = deepcopy(self.config.propagation)
        est_prop_cfg.propagation_model = self.config.estimation.sequential_filter.dynamics_model

        estimate_agents: dict[int, EstimateAgent] = {}
        for target_config in self.validated_target_configs.values():
            filter_dynamics = dynamicsFactory(
                target_config,
                est_prop_cfg,
                self.config.geopotential,
                self.config.perturbations,
                self.clock,
            )

            estimate_agents[target_config.id] = EstimateAgent.fromConfig(
                tgt_cfg=target_config,
                clock=self.clock,
                dynamics=filter_dynamics,
                time_cfg=self.config.time,
                noise_cfg=self.config.noise,
                estimation_cfg=self.config.estimation,
            )

        self.logger.info(f"Successfully loaded {len(estimate_agents)} estimate agents")
        return estimate_agents

    def _initSensors(self) -> dict[int, SensingAgent]:
        """Initialize sensor agents based on a given config.

        Returns:
            ``dict``: constructed :class:`.SensingAgent` objects for each specified agent
        """
        sensing_agents: dict[int, SensingAgent] = {}
        for sensor_agent_config in self.validated_sensor_configs.values():
            # Assign Sensor FoV from init if not set
            if self.config.observation.background:
                sensor_agent_config.sensor.background_observations = True

            dynamics = dynamicsFactory(
                sensor_agent_config,
                self.config.propagation,
                self.config.geopotential,
                self.config.perturbations,
                self.clock,
            )

            sensing_agents[sensor_agent_config.id] = SensingAgent.fromConfig(
                sen_cfg=sensor_agent_config,
                clock=self.clock,
                dynamics=dynamics,
                prop_cfg=self.config.propagation,
            )

        self.logger.info(f"Successfully loaded {len(sensing_agents)} sensor agents")
        return sensing_agents

    def _loadAgentsIntoDatabase(self, database: ResonaateDatabase) -> None:
        """Load agent objects into database.

        Args:
            database (ResonaateDatabase): reference to the simulation database.
        """
        agent_data = [
            AgentModel(unique_id=tgt.simulation_id, name=tgt.name)
            for tgt in self.target_agents.values()
        ]
        agent_data.extend(
            AgentModel(unique_id=sen.simulation_id, name=sen.name)
            for sen in self.sensor_agents.values()
        )

        database.bulkSave(agent_data)

    def _loadEventsIntoDatabase(self, database: ResonaateDatabase) -> None:
        """Load event objects into the database.

        Args:
            database (ResonaateDatabase): reference to the simulation database.

        Raises:
            ValueError: if an event is missing a data dependency.
        """
        built_event_types = set()
        built_events = []
        for event_config in sorted(self._config.events, key=lambda x: x.start_time):
            for data_dependency in event_config.getDataDependencies():
                if found_dependency := database.getData(  # noqa: F841
                    data_dependency.query,
                    multi=False,
                ):
                    continue

                # else
                try:
                    new_dependency = data_dependency.createDependency()
                except MissingDataDependencyError as missing_dep:
                    err = f"Event {event_config.event_type!r} is missing a data dependency."
                    raise ValueError(err) from missing_dep

                self.logger.debug(f"Creating event data dependency: {new_dependency}")
                database.insertData(new_dependency)

            built_event_types.add(event_config.event_type)
            built_events.append(Event.concreteFromConfig(event_config))

        if built_events:
            database.insertData(*built_events)

        self.logger.info(f"Loaded {len(built_events)} events of types {built_event_types}")

    def _validateTargetAgents(self, engine_config: EngineConfig) -> None:
        """Throw an `DuplicateTargetError` if the `new_target` and `existing_target` states don't match.

        Args:
            engine_config (:class:`.EngineConfig`): engine config from which a target is added.

        Returns:
            ``list``: validated target agent IDs

        Raises:
            :exc:`.DuplicateTargetError`: If the `new_target` and `existing_target` states don't match.
        """
        engine_targets: list[int] = []
        target_agent: AgentConfig
        for target_agent in engine_config.targets:
            existing_target = self.validated_target_configs.get(target_agent.id)
            if existing_target and existing_target.state != target_agent.state:
                err = (
                    f"Duplicate targets specified with different initial states: {target_agent.id}"
                )
                raise DuplicateTargetError(err)

            engine_targets.append(target_agent.id)
            self.validated_target_configs[target_agent.id] = target_agent

        return engine_targets

    def _validateSensingAgents(self, engine_config: EngineConfig) -> None:
        """Throw an `DuplicateSensorError` if there are duplicate sensing agents.

        Args:
            engine_config (:class:`.EngineConfig`): engine config from which a target is added.

        Returns:
            ``list``: validated sensor agent IDs

        Raises:
            :exc:`.DuplicateSensorError`: there is already another sensing agent with the same ID.
        """
        engine_sensors: list[int] = []
        sensor_agent: SensingAgentConfig
        for sensor_agent in engine_config.sensors:
            if self.validated_sensor_configs.get(sensor_agent.id):
                err = f"Sensor can't be tasked by two engines: {sensor_agent.id}"
                raise DuplicateSensorError(err)

            engine_sensors.append(sensor_agent.id)
            self.validated_sensor_configs[sensor_agent.id] = sensor_agent

        return engine_sensors

    @property
    def config(self) -> ScenarioConfig:
        """:class:`.ScenarioConfig`: returns the entire configuration."""
        return self._config
