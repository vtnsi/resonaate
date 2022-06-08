# Standard Library Imports
# Third Party Imports
from numpy import asarray
from numpy.random import default_rng
# RESONAATE Imports
from .scenario_config import ScenarioConfig
from ..agents.target_agent import TargetAgent
from ..agents.estimate_agent import EstimateAgent
from ..agents.sensing_agent import SensingAgent
from ..common.behavioral_config import BehavioralConfig
from ..common.logger import Logger
from ..data.data_interface import DataInterface
from ..dynamics import spacecraftDynamicsFactory
from ..events.impulsive import Impulsive
from ..events.propulsion import Propulsion
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
            scenario_configuration (``dict``): config settings to make a valid :class:`.Scenario`

        Raises:
            ValueError: raised if the "engines" field is empty
        """
        # Create logger from configs
        self.logger = Logger("resonaate", path=BehavioralConfig.getConfig().logging.OutputLocation)
        # Save base config
        self._config = ScenarioConfig(scenario_configuration)
        # Check to make sure these ar not empty lists
        if not self._config.engines:
            self.logger.error("You must include valid list of engines in Scenario config.")
            raise ValueError

        # Instantiate clock based on config's start time and class variables
        self.clock = ScenarioClock.fromConfig(self.time)

        # Target event parsing
        if self._config.target_events:
            target_events = self.initTargetEvents(self._config.target_events, self.clock)
            for target, events in target_events.items():
                types = set()
                for event in events:
                    # Can't use `isinstance` here, because `types` is not a tuple. Additionally,
                    #   since this data-collection is really just being used for condensed logging
                    #   purposes, using `isinstance` would actually hide subclasses from the logs.
                    if type(event) not in types:  # pylint: disable=unidiomatic-typecheck
                        types.add(type(event))
                self.logger.info("Loaded {0} events with types {1} for target {2}.".format(
                    len(events),
                    types,
                    target
                ))
        else:
            target_events = []
        self._target_events = target_events

        # Sensor event parsing
        if self._config.sensor_events:
            pass
        else:
            sensor_events = []
        self._sensor_events = sensor_events

        self.logger.info(
            "Successfully loaded {0} events".format(
                len(self._target_events) + len(self._sensor_events)
            )
        )

        # Create the base estimation filter for nominal operation
        # [TODO]: UKF parameters should be configurable
        self._filter_config = {
            "filter_type": self.config.filter['name'],
            # Create dynamics object for RSO filter propagation
            "dynamics": spacecraftDynamicsFactory(
                self.propagation["propagation_model"],
                self.clock,
                self.geopotential,
                self.perturbations,
                method=self.propagation["integration_method"]
            ),
            # Create process noise covariance for uncertainty propagation
            "process_noise": noiseCovarianceFactory(
                self.noise["filter_noise_type"],
                self.time["physics_step_sec"],
                self.noise["filter_noise_magnitude"]
            ),
            "alpha": 0.05,
            "beta": 2.0,
        }

        # Seed the pseudo-random number generator with either None, or [0, 2**32-1].
        # None results in the rng reading /dev/urandom or the clock.
        random_seed = self.noise["random_seed"]
        if not isinstance(random_seed, int) and random_seed is not None:
            self.logger.error("Random seed value must be positive, non-zero integer")
            raise ValueError(random_seed)

        ## Init database if necessary
        preloaded_ephem = BehavioralConfig.getConfig().database.EphemerisPreLoaded
        if not self.propagation["realtime_propagation"] and preloaded_ephem is False:
            shared_interface = DataInterface.getSharedInterface()
            shared_interface.initDatabaseFromJSON(
                BehavioralConfig.getConfig().database.PhysicsModelDataPath
            )

        # create target and sensor sets
        estimate_set = set()
        target_dict = {}
        sensor_dict = {}
        self.targets_agents = {}
        self.estimate_agents = {}
        self.tasking_engines = []

        for engine in self._config.engines:
            # Create Reward & Decision from configuration
            reward = rewardsFactory(engine['reward'])
            self.logger.info(
                "Reward function: {0}".format(
                    reward.__class__.__name__
                )
            )
            decision = decisionFactory(engine['decision'])
            self.logger.info(
                "Decision function: {0}".format(
                    decision.__class__.__name__
                )
            )
            if engine['decision']['name'] == 'AllVisibleDecision':
                for sensor in engine['sensors']:
                    assert sensor['sensor_type'] == 'AdvRadar', "Only AdvRadar sensors can use the AllVisibleDecision"

            # Build target and estimate sets
            engine_targets = []
            for rso in engine['targets']:
                engine_targets.append(rso['sat_num'])
                estimate_set.add(rso['sat_num'])
                target_dict[rso['sat_num']] = rso

            # Build sensor set
            engine_sensors = []
            for sensor in engine['sensors']:
                engine_sensors.append(sensor['id'])
                sensor_dict[sensor['id']] = sensor

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

        self.target_agents = self.initTargets(target_dict)

        self.logger.info(
            "Successfully loaded {0} target agents".format(
                len(self.target_agents)
            )
        )
        # Reformat list of sensors
        sensor_list = list(sensor_dict.values())

        self.sensor_network = []
        for agent in sensor_list:
            config = {
                "agent": agent,
                "clock": self.clock,
                "satellite_dynamics": spacecraftDynamicsFactory(
                    self.propagation["propagation_model"],
                    self.clock,
                    self.geopotential,
                    self.perturbations,
                    method=self.propagation["integration_method"]
                ),
                "realtime": self.propagation["realtime_propagation"]
            }

            self.sensor_network.append(
                SensingAgent.fromConfig(config, events=[])
            )

        self.logger.info(
            "Successfully loaded sensor network"
        )

        self.logger.info(
            "Successfully loaded {0} sensor agents".format(
                len(self.sensor_network)
            )
        )

        # Build estimate set
        self.estimate_agents = {}
        for target_id, target_agent in self.target_agents.items():
            config = {
                "target": target_agent,
                "init_estimate_error": self.noise["initial_error_magnitude"],
                "rng": default_rng(random_seed),
                "clock": self.clock,
                "filter": self._filter_config,
                "seed": random_seed
            }
            self.estimate_agents[target_id] = EstimateAgent.fromConfig(config, events=[])

    def initTargets(self, targets_conf):
        """Initialize target RSOs based on a given config.

        Args:
            targets_conf (``list``): formatted ``dict`` s describing target RSO attributes

        Raises:
            ValueError: raised if RSO state isn't specified as "init_coe" or "init_eci"

        Returns:
            ``dict``: constructed :class:`.Spacecraft` objects for each RSO specified
        """
        targets = {}
        for key in targets_conf:
            dynamics_method = spacecraftDynamicsFactory(
                self.propagation["propagation_model"],
                self.clock,
                self.geopotential,
                self.perturbations,
                method=self.propagation["integration_method"]
            )

            dynamics_noise = noiseCovarianceFactory(
                self.noise["dynamics_noise_type"],
                self.time["physics_step_sec"],
                self.noise["dynamics_noise_magnitude"]
            )

            config = {
                "target": targets_conf[key],
                "clock": self.clock,
                "dynamics": dynamics_method,
                "realtime": self.propagation["realtime_propagation"],
                "noise": dynamics_noise,
                "random_seed": self.noise["random_seed"]
            }
            targets[key] = TargetAgent.fromConfig(config, events=[])

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
            if isinstance(event, Propulsion):
                propulsion.append(event)
            else:
                raise NotImplementedError("Not set up to handle events other than propulsions.")

        return propulsion

    @staticmethod
    def initTargetEvents(events_conf, clock):
        """Initialize target events based on event configuration.

        Args:
            events_conf (``list``): events formatted as specified in the RESONAATE README.
            clock (:class:`.ScenarioClock`): global clock object used for the simulation.

        Returns:
            (``list``): initialized target events
        """
        target_events = {}
        for event in events_conf:
            target_event = ScenarioBuilder._createEvent(event, clock)

            for target in event["affected_targets"]:
                try:
                    target_events[target].append(target_event)
                except KeyError:
                    target_events[target] = [target_event]

        return target_events

    @staticmethod
    def _createEvent(event_conf, clock):
        """Create event object based on given configuration.

        Args:
        event_conf (``dict``): event definition
        clock (:class:`.ScenarioClock`): global clock object used for the simulation.

        Returns:
            (:class:`.Event`): constructed event object
        """
        target_event = None
        message = "Delta vector defining an impulsive maneuver should be 3 dimensional, not"
        if event_conf["event_type"] == "IMPULSE":
            assert len(event_conf["delta_v"]) == 3, "{0} {1}.".format(message, len(event_conf["delta_v"]))
            delta_v = asarray(event_conf["delta_v"])
            delta_v = delta_v.reshape(3)

            julian_date = JulianDate(event_conf["julian_date"])
            assert julian_date >= clock.julian_date_start

            target_event = Impulsive(clock, julian_date.convertToScenarioTime(clock.julian_date_start), delta_v)

        else:
            raise Exception("Unable to handle event type '{0}'".format(event_conf["event_type"]))

        return target_event

    @property
    def config(self):
        """``dict``: returns the entire configuration."""
        return self._config

    @property
    def noise(self):
        """``dict``: returns "noise" section of the configuration."""
        return self._config.noise

    @property
    def propagation(self):
        """``dict``: returns "propagation" section of the configuration."""
        return self._config.propagation

    @property
    def time(self):
        """``dict``: returns "time" section of the configuration."""
        return self._config.time

    @property
    def geopotential(self):
        """``dict``: returns "geopotential" section of the configuration."""
        return self._config.geopotential

    @property
    def perturbations(self):
        """``dict``: returns "perturbations" section of the configuration."""
        return self._config.perturbations
