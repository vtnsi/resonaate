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
from ..data.data_interface import AgentModel
from ..data.events import Event
from ..data.resonaate_database import ResonaateDatabase
from ..dynamics import dynamicsFactory
from ..tasking.decisions import decisionFactory
from ..tasking.engine.centralized_engine import CentralizedTaskingEngine
from ..tasking.rewards import rewardsFactory
from .clock import ScenarioClock
from .config.event_configs import MissingDataDependency

# Type Checking Imports
if TYPE_CHECKING:
    # Local Imports
    from ..tasking.engine.engine_base import TaskingEngine
    from .config import EngineConfig, ScenarioConfig, SensingAgentConfig, TargetAgentConfig


class ScenarioBuilder:
    """Builder pattern to create a :class:`.Scenario` object from a configuration dict.

    This contains the requisite logic to properly build all the supplementary objects required to
    properly construct a :class:`.Scenario` object.
    """

    # pylint:disable=too-many-locals, too-many-branches
    def __init__(  # noqa: C901
        self, scenario_configuration: ScenarioConfig, importer_db_path: str | None = None
    ) -> None:
        """Instantiate a :class:`.ScenarioBuilder` from a config dictionary.

        Args:
            scenario_configuration (:class:`.ScenarioConfig`): config settings to make a valid :class:`.Scenario`
            importer_db_path (``str``, optional): path to external importer database for pre-canned
                data. Defaults to ``None``.

        Raises:
            ValueError: raised if the "engines" field is empty
        """
        # [FIXME]: Split this into more sub-methods
        # Create logger from configs
        self.logger = Logger("resonaate", path=BehavioralConfig.getConfig().logging.OutputLocation)
        # Save base config
        self._config = scenario_configuration

        # Instantiate clock based on config's start time and class variables
        self.clock = ScenarioClock.fromConfig(self.config.time)

        # create target and sensor sets
        target_configs: dict[int, TargetAgentConfig] = {}
        sensor_configs: dict[int, SensingAgentConfig] = {}
        self.tasking_engines: dict[int, TaskingEngine] = {}

        engine_conf: EngineConfig
        for engine_conf in self._config.engines:
            if engine_conf.unique_id in self.tasking_engines:
                err = f"Engines share a unique ID: {engine_conf.unique_id}"
                raise DuplicateEngineError(err)

            # Create Reward & Decision from configuration
            reward = rewardsFactory(engine_conf.reward)
            self.logger.info(f"Reward function: {reward.__class__.__name__}")
            decision = decisionFactory(engine_conf.decision)
            self.logger.info(f"Decision function: {decision.__class__.__name__}")

            # Build target and estimate sets
            engine_targets = []
            tgt: TargetAgentConfig
            for tgt in engine_conf.targets:
                engine_targets.append(tgt.id)

                existing_target = target_configs.get(tgt.id)
                if existing_target:
                    self._validateTargetAddition(tgt, existing_target)
                target_configs[tgt.id] = tgt

            # Build sensor set
            engine_sensors = []
            sensor_agent: SensingAgentConfig
            for sensor_agent in engine_conf.sensors:
                engine_sensors.append(sensor_agent.id)

                if sensor_configs.get(sensor_agent.id):
                    err = f"Sensor can't be tasked by two engines: {sensor_agent.id}"
                    raise DuplicateSensorError(err)
                sensor_configs[sensor_agent.id] = sensor_agent

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

            self.tasking_engines[tasking_engine.unique_id] = tasking_engine
            self.logger.info(
                f"Successfully built tasking engine: {tasking_engine.__class__.__name__}"
            )

        self.target_agents = self.initTargets(list(target_configs.values()))

        # Build estimate set
        self.estimate_agents: dict[int, EstimateAgent] = {}
        est_prop_cfg = deepcopy(self.config.propagation)
        est_prop_cfg.propagation_model = self.config.estimation.sequential_filter.dynamics_model
        for target_id, target_config in target_configs.items():

            # Create the base estimation filter for nominal operation
            filter_dynamics = dynamicsFactory(
                target_config,
                est_prop_cfg,
                self.config.geopotential,
                self.config.perturbations,
                self.clock,
            )

            self.estimate_agents[target_id] = EstimateAgent.fromConfig(
                tgt_cfg=target_config,
                clock=self.clock,
                dynamics=filter_dynamics,
                prop_cfg=self.config.propagation,
                time_cfg=self.config.time,
                noise_cfg=self.config.noise,
                estimation_cfg=self.config.estimation,
            )

        self.logger.info(f"Successfully loaded {len(self.target_agents)} target agents")

        self.sensor_network: list[SensingAgent] = []
        for sensor_agent_config in sensor_configs.values():
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

            self.sensor_network.append(
                SensingAgent.fromConfig(
                    sen_cfg=sensor_agent_config,
                    clock=self.clock,
                    dynamics=dynamics,
                    prop_cfg=self.config.propagation,
                )
            )

        self.logger.info(f"Successfully loaded {len(self.sensor_network)} sensor agents")

        # Store agent data in the database for events that rely on them
        agent_data = []
        for target_agent in self.target_agents.values():
            agent_data.append(
                AgentModel(unique_id=target_agent.simulation_id, name=target_agent.name)
            )
        for sensor_agent in self.sensor_network:
            agent_data.append(
                AgentModel(unique_id=sensor_agent.simulation_id, name=sensor_agent.name)
            )

        shared_interface = ResonaateDatabase.getSharedInterface()
        shared_interface.bulkSave(agent_data)

        built_event_types = set()
        built_events = []
        for event_config in sorted(self._config.events, key=lambda x: x.start_time):
            for data_dependency in event_config.getDataDependencies():
                found_dependency = shared_interface.getData(data_dependency.query, multi=False)
                if found_dependency is None:
                    try:
                        new_dependency = data_dependency.createDependency()
                    except MissingDataDependency as missing_dep:
                        err = f"Event {event_config.event_type!r} is missing a data dependency."
                        raise ValueError(err) from missing_dep
                    else:
                        self.logger.info(f"Creating event data dependency: {new_dependency}")
                        shared_interface.insertData(new_dependency)

            built_event_types.add(event_config.event_type)
            built_events.append(Event.concreteFromConfig(event_config))

        if built_events:
            shared_interface.insertData(*built_events)
        self.logger.info(f"Loaded {len(built_events)} events of types {built_event_types}")

    @staticmethod
    def _validateTargetAddition(
        new_target: TargetAgentConfig, existing_target: TargetAgentConfig
    ) -> None:
        """Throw an `DuplicateTargetError` if the `new_target` and `existing_target` states don't match.

        Args:
            new_target (:class:`.TargetAgentConfig`): Target object being added.
            existing_target (:class:`.TargetAgentConfig`): Existing target object.

        Raises:
            :exc:`.DuplicateTargetError`: If the `new_target` and `existing_target` states don't match.
        """
        if existing_target.state == new_target.state:
            return

        err = f"Duplicate targets specified with different initial states: {new_target.id}"
        raise DuplicateTargetError(err)

    def initTargets(
        self,
        target_configs: list[TargetAgentConfig],
    ) -> dict[int, TargetAgent]:
        """Initialize target RSOs based on a given config.

        Args:
            target_configs (``list``): :class:`.TargetAgentConfig` objects describing target RSO attributes.

        Returns:
            ``dict``: constructed :class:`.Spacecraft` objects for each RSO specified
        """
        targets: dict[int, TargetAgent] = {}
        for tgt_cfg in target_configs:
            dynamics = dynamicsFactory(
                tgt_cfg,
                self.config.propagation,
                self.config.geopotential,
                self.config.perturbations,
                self.clock,
            )

            targets[tgt_cfg.id] = TargetAgent.fromConfig(
                tgt_cfg=tgt_cfg,
                clock=self.clock,
                dynamics=dynamics,
                prop_cfg=self.config.propagation,
            )

        return targets

    @property
    def config(self) -> ScenarioConfig:
        """:class:`.ScenarioConfig`: returns the entire configuration."""
        return self._config
