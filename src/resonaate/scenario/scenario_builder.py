# Standard Library Imports
from collections import defaultdict
from math import isclose
# Third Party Imports
from numpy import asarray, allclose
from numpy.random import default_rng
# RESONAATE Imports
from ..agents.target_agent import TargetAgent
from ..agents.estimate_agent import EstimateAgent
from ..agents.sensing_agent import SensingAgent
from ..common.behavioral_config import BehavioralConfig
from ..common.logger import Logger
from ..dynamics import spacecraftDynamicsFactory
from ..dynamics.integration_events.scheduled_impulse import ScheduledImpulse, ScheduledNTWImpulse
from ..physics.noise import noiseCovarianceFactory
from ..physics.time.stardate import JulianDate
from ..scenario.clock import ScenarioClock
from ..tasking.decisions import decisionFactory
from ..tasking.engine.centralized_engine import CentralizedTaskingEngine
from ..tasking.rewards import rewardsFactory


class ScenarioBuilder:
    """Builder pattern to create a :class:`.Scenario` object from a configuration dict.

    This contains the requisite logic to properly build all the supplementary objects required to
    properly construct a :class:`.Scenario` object.
    """

    # pylint:disable=too-many-locals
    def __init__(self, scenario_configuration):  # noqa: C901
        """Instantiate a :class:`.ScenarioBuilder` from a config dictionary.

        Args:
            scenario_configuration (ScenarioConfig): config settings to make a valid :class:`.Scenario`

        Raises:
            ValueError: raised if the "engines" field is empty
        """
        # Create logger from configs
        self.logger = Logger("resonaate", path=BehavioralConfig.getConfig().logging.OutputLocation)
        # Save base config
        self._config = scenario_configuration

        # Instantiate clock based on config's start time and class variables
        self.clock = ScenarioClock.fromConfig(self.time)

        # Target event parsing
        self._target_events = self.initTargetEvents()

        # Sensor event parsing
        self._sensor_events = self.initSensorEvents()

        self.logger.info(
            "Successfully loaded {0} events".format(
                len(self._target_events) + len(self._sensor_events)
            )
        )

        # Create the base estimation filter for nominal operation
        # [TODO]: UKF parameters should be configurable
        self._filter_config = {
            "filter_type": self.config.filter.name,
            # Create dynamics object for RSO filter propagation
            "dynamics": spacecraftDynamicsFactory(
                self.config.filter.dynamics,
                self.clock,
                self.geopotential,
                self.perturbations,
                method=self.propagation.integration_method
            ),
            # Create process noise covariance for uncertainty propagation
            "process_noise": noiseCovarianceFactory(
                self.noise.filter_noise_type,
                self.time.physics_step_sec,
                self.noise.filter_noise_magnitude
            )
        }
        self._filter_config.update(self.config.filter.parameters)

        # create target and sensor sets
        target_configs = {}
        sensor_configs = {}
        self.tasking_engines = []

        for engine_conf in self._config.engines.objects:
            # Create Reward & Decision from configuration
            reward = rewardsFactory(engine_conf.reward)
            self.logger.info(
                "Reward function: {0}".format(
                    reward.__class__.__name__
                )
            )
            decision = decisionFactory(engine_conf.decision)
            self.logger.info(
                "Decision function: {0}".format(
                    decision.__class__.__name__
                )
            )

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
                    raise Exception(err)
                sensor_configs[sensor.id] = sensor

            # Create the tasking engine object
            tasking_engine = CentralizedTaskingEngine(
                engine_sensors,
                engine_targets,
                reward,
                decision
            )

            self.tasking_engines.append(tasking_engine)
            self.logger.info(
                "Successfully built tasking engine: {0}".format(
                    tasking_engine.__class__.__name__
                )
            )

        self.target_agents = self.initTargets(list(target_configs.values()))

        # Build estimate set
        self.estimate_agents = {}
        for target_id, target_agent in self.target_agents.items():
            config = {
                "target": target_agent,
                "init_estimate_error": self.noise.initial_error_magnitude,
                "rng": default_rng(self.noise.random_seed),
                "clock": self.clock,
                "filter": self._filter_config,
                "seed": self.noise.random_seed
            }
            self.estimate_agents[target_id] = EstimateAgent.fromConfig(config, events=[])

        self.logger.info(
            "Successfully loaded {0} target agents".format(
                len(self.target_agents)
            )
        )

        self.sensor_network = []
        for agent in sensor_configs.values():
            config = {
                "agent": agent,
                "clock": self.clock,
                "satellite_dynamics": spacecraftDynamicsFactory(
                    self.propagation.propagation_model,
                    self.clock,
                    self.geopotential,
                    self.perturbations,
                    method=self.propagation.integration_method
                ),
                "realtime": self.propagation.realtime_propagation
            }

            self.sensor_network.append(
                SensingAgent.fromConfig(config, events=[])
            )

        self.logger.info(
            "Successfully loaded {0} sensor agents".format(
                len(self.sensor_network)
            )
        )

    @staticmethod
    def _validateTargetAddition(new_target, existing_target):
        """Throw an ``Exception`` if `new_target` and `existing_target`'s states don't match.

        Args:
            new_target (TargetConfigObject): Target object being added.
            existing_target (TargetConfigObject): Existing target object.

        Raises:
            Exception: If `new_target` and `existing_target`s states don't match.
        """
        if existing_target.eci_set and new_target.eci_set:
            eci_equal = allclose(
                asarray(existing_target.init_eci),
                asarray(new_target.init_eci)
            )
            if eci_equal:
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
        raise Exception(err)

    def initTargets(self, target_configs):
        """Initialize target RSOs based on a given config.

        Args:
            target_configs (``list``): List of :class:`.TargetConfigObject`s describing target RSO
                attributes.

        Raises:
            ValueError: raised if RSO state isn't specified as "init_coe" or "init_eci"

        Returns:
            ``dict``: constructed :class:`.Spacecraft` objects for each RSO specified
        """
        targets = {}
        for target_conf in target_configs:
            dynamics_method = spacecraftDynamicsFactory(
                self.propagation.propagation_model,
                self.clock,
                self.geopotential,
                self.perturbations,
                method=self.propagation.integration_method
            )

            dynamics_noise = noiseCovarianceFactory(
                self.noise.dynamics_noise_type,
                self.time.physics_step_sec,
                self.noise.dynamics_noise_magnitude
            )

            config = {
                "target": target_conf,
                "clock": self.clock,
                "dynamics": dynamics_method,
                "realtime": self.propagation.realtime_propagation,
                "station_keeping": target_conf.station_keeping,
                "noise": dynamics_noise,
                "random_seed": self.noise.random_seed
            }
            targets[target_conf.sat_num] = TargetAgent.fromConfig(config, events=[])

        return targets

    @staticmethod
    def _getPropulsionFromEvents(cur_events):
        """Parse the propulsion objects from a list of events.

        Args:
            cur_events (``list``): event objects as dictionaries

        Raises:
            NotImplementedError: raised if events are not an implemented type

        Returns:
            ``list``: :class:`.Propulsion` event objects
        """
        propulsion = []
        for event in cur_events:
            if isinstance(event, ScheduledImpulse):
                propulsion.append(event)
            else:
                raise NotImplementedError("Not set up to handle events other than propulsions.")

        return propulsion

    def initTargetEvents(self):
        """Initialize target events based on event configuration.

        Returns:
            dict: Initialized target events (or empty dictionary if there were no configured
                events).
        """
        if self._config.target_events.objects:
            target_events = defaultdict(list)
            target_event_types = defaultdict(set)
            for event in self._config.target_events.objects:
                target_event = ScenarioBuilder._createEvent(event, self.clock)

                for target in event.affected_targets:
                    target_events[target].append(target_event)
                    target_event_types[target].add(type(target_event))

            for target in target_events.keys():
                self.logger.info("Loaded {0} events with types {1} for target {2}.".format(
                    len(target_events[target]),
                    target_event_types[target],
                    target
                ))

            return target_events
        # else:
        return {}

    def initSensorEvents(self):  # pylint: disable=no-self-use
        """Initialize sensor events based on configuration.

        Returns:
            dict: Initialized sensor events (or empty dictionary if there were no configured
                events).

        Note:
            This method is a stub.

        Todo:
            - Implement this.

        """
        return {}

    @staticmethod
    def _createEvent(event_conf, clock):
        """Create event object based on given configuration.

        Args:
            event_conf (TargetEventConfigObject): event definition
            clock (:class:`.ScenarioClock`): global clock object used for the simulation.

        Returns:
            (:class:`.Event`): constructed event object
        """
        target_event = None
        if event_conf.event_type == "IMPULSE":
            delta_v = asarray(event_conf.delta_v)
            delta_v = delta_v.reshape(3)

            julian_date = JulianDate(event_conf.julian_date)
            if julian_date < clock.julian_date_start:
                err = "Event takes place before scenario: {0}".format(julian_date)
                raise ValueError(err)

            target_event = ScheduledNTWImpulse(julian_date.convertToScenarioTime(clock.julian_date_start), delta_v)

        else:
            raise Exception("Unable to handle event type '{0}'".format(event_conf["event_type"]))

        return target_event

    @property
    def config(self):
        """ScenarioConfig: returns the entire configuration."""
        return self._config

    @property
    def noise(self):
        """NoiseConfig: returns "noise" section of the configuration."""
        return self._config.noise

    @property
    def propagation(self):
        """PropagationConfig`: returns "propagation" section of the configuration."""
        return self._config.propagation

    @property
    def time(self):
        """TimeConfig: returns "time" section of the configuration."""
        return self._config.time

    @property
    def geopotential(self):
        """GeopotentialConfig: returns "geopotential" section of the configuration."""
        return self._config.geopotential

    @property
    def perturbations(self):
        """PerturbationsConfig: returns "perturbations" section of the configuration."""
        return self._config.perturbations
