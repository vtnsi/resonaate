"""Defines the :class:`.ScenarioBuilder` class to build valid :class:`.Scenario` objects from given configurations."""
from __future__ import annotations

# Standard Library Imports
from math import isclose
from typing import TYPE_CHECKING

# Third Party Imports
from numpy import allclose, array
from numpy.random import default_rng

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
from ..dynamics import spacecraftDynamicsFactory
from ..dynamics.special_perturbations import calcSatRatio
from ..physics.noise import noiseCovarianceFactory
from ..tasking.decisions import decisionFactory
from ..tasking.engine.centralized_engine import CentralizedTaskingEngine
from ..tasking.rewards import rewardsFactory
from .clock import ScenarioClock
from .config.event_configs import MissingDataDependency

# Type Checking Imports
if TYPE_CHECKING:
    # Local Imports
    from ..tasking.engine.engine_base import TaskingEngine
    from .config import ScenarioConfig
    from .config.agent_configs import SensingAgentConfig, TargetAgentConfig


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

        q_matrix = noiseCovarianceFactory(
            self.config.noise.filter_noise_type,
            self.config.time.physics_step_sec,
            self.config.noise.filter_noise_magnitude,
        )

        # create target and sensor sets
        target_configs: dict[int, TargetAgentConfig] = {}
        sensor_configs: dict[int, SensingAgentConfig] = {}
        self.tasking_engines: dict[int, TaskingEngine] = {}

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
            for rso in engine_conf.targets:
                engine_targets.append(rso.sat_num)

                existing_target = target_configs.get(rso.sat_num)
                if existing_target:
                    self._validateTargetAddition(rso, existing_target)
                target_configs[rso.sat_num] = rso

            # Build sensor set
            engine_sensors = []
            for sensor in engine_conf.sensors:
                engine_sensors.append(sensor.id)

                if sensor_configs.get(sensor.id):
                    err = f"Sensor can't be tasked by two engines: {sensor.id}"
                    raise DuplicateSensorError(err)
                sensor_configs[sensor.id] = sensor

            # Create the tasking engine object
            tasking_engine = CentralizedTaskingEngine(
                engine_conf.unique_id,
                engine_sensors,
                engine_targets,
                reward,
                decision,
                importer_db_path,
                self.config.propagation.realtime_observation,
            )

            self.tasking_engines[tasking_engine.unique_id] = tasking_engine
            self.logger.info(
                f"Successfully built tasking engine: {tasking_engine.__class__.__name__}"
            )

        self.target_agents = self.initTargets(
            list(target_configs.values()), self.config.propagation.station_keeping
        )

        # Build estimate set
        self.estimate_agents: dict[int, EstimateAgent] = {}
        for target_id, target_config in target_configs.items():
            sat_ratio = calcSatRatio(
                target_config.visual_cross_section,
                target_config.mass,
                target_config.reflectivity,
            )

            # Create the base estimation filter for nominal operation
            filter_dynamics = spacecraftDynamicsFactory(
                self.config.estimation.sequential_filter.dynamics_model,
                self.clock,
                self.config.geopotential,
                self.config.perturbations,
                sat_ratio,
                method=self.config.propagation.integration_method,
            )

            config = {
                "target": target_config,
                "agent_type": self.target_agents[target_id].agent_type,
                "position_std": self.config.noise.init_position_std_km,
                "velocity_std": self.config.noise.init_velocity_std_km_p_sec,
                "rng": default_rng(self.config.noise.random_seed),
                "clock": self.clock,
                "sequential_filter": self.config.estimation.sequential_filter,
                "adaptive_filter": self.config.estimation.adaptive_filter,
                "seed": self.config.noise.random_seed,
                "dynamics": filter_dynamics,
                "q_matrix": q_matrix,
            }
            self.estimate_agents[target_id] = EstimateAgent.fromConfig(config)

        self.logger.info(f"Successfully loaded {len(self.target_agents)} target agents")

        self.sensor_network: list[SensingAgent] = []
        for sensor_config in sensor_configs.values():
            # Assign Sensor FoV from init if not set
            if self.config.observation.field_of_view:
                sensor_config.calculate_fov = True
            sat_ratio = calcSatRatio(
                sensor_config.visual_cross_section,
                sensor_config.mass,
                sensor_config.reflectivity,
            )

            config = {
                "agent": sensor_config,
                "clock": self.clock,
                "satellite_dynamics": spacecraftDynamicsFactory(
                    self.config.propagation.propagation_model,
                    self.clock,
                    self.config.geopotential,
                    self.config.perturbations,
                    sat_ratio,
                    method=self.config.propagation.integration_method,
                ),
                "realtime": self.config.propagation.sensor_realtime_propagation,
            }

            self.sensor_network.append(SensingAgent.fromConfig(config))

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
                        err = f"Event '{event_config.event_type}' is missing a data dependency."
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
        if existing_target.eci_set and new_target.eci_set:
            if allclose(array(existing_target.init_eci), array(new_target.init_eci)):
                return

        if existing_target.eqe_set and new_target.eqe_set:
            if allclose(array(existing_target.eqe_set), array(new_target.eqe_set)):
                return

        if existing_target.coe_set and new_target.coe_set:
            if len(existing_target.init_coe) == len(new_target.init_coe):
                orbit_matches = True
                for orbit_param, existing_setting in existing_target.init_coe.items():
                    if not isclose(existing_setting, new_target.init_coe[orbit_param]):
                        orbit_matches = False

                if orbit_matches:
                    return

        err = f"Duplicate targets specified with different initial states: {new_target.sat_num}"
        raise DuplicateTargetError(err)

    def initTargets(
        self,
        target_configs: list[TargetAgentConfig],
        station_keeping: bool,
    ) -> dict[int, TargetAgent]:
        """Initialize target RSOs based on a given config.

        Args:
            target_configs (``list``): :class:`.TargetAgentConfig` objects describing target RSO attributes.
            station_keeping (``bool``): whether to perform station-keeping burns during the scenario.

        Raises:
            ValueError: raised if RSO state isn't specified as "init_coe" or "init_eci"

        Returns:
            ``dict``: constructed :class:`.Spacecraft` objects for each RSO specified
        """
        targets: dict[int, TargetAgent] = {}
        for target_conf in target_configs:
            sat_ratio = calcSatRatio(
                target_conf.visual_cross_section,
                target_conf.mass,
                target_conf.reflectivity,
            )

            dynamics_method = spacecraftDynamicsFactory(
                self.config.propagation.propagation_model,
                self.clock,
                self.config.geopotential,
                self.config.perturbations,
                sat_ratio,
                method=self.config.propagation.integration_method,
            )

            dynamics_noise = noiseCovarianceFactory(
                self.config.noise.dynamics_noise_type,
                self.config.time.physics_step_sec,
                self.config.noise.dynamics_noise_magnitude,
            )
            config = {
                "target": target_conf,
                "clock": self.clock,
                "dynamics": dynamics_method,
                "realtime": self.config.propagation.target_realtime_propagation,
                "station_keeping": station_keeping,
                "noise": dynamics_noise,
                "random_seed": self.config.noise.random_seed,
            }
            targets[target_conf.sat_num] = TargetAgent.fromConfig(config)

        return targets

    @property
    def config(self) -> ScenarioConfig:
        """:class:`.ScenarioConfig`: returns the entire configuration."""
        return self._config
