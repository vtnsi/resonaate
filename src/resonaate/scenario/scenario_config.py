# Standard Library Imports
from logging import getLogger
from datetime import datetime
# Third Party Imports
# RESONAATE Imports


class ScenarioConfig:
    """Configuration class for creating valid :class:`.Scenario`s.

    This allows the extra logic for properly checking all configs to be abstracted from the
    factory methods and the :class:`.Scenario`'s constructor.
    """

    CONFIG = {
        "time": {
            "start_timestamp": {
                "default": None,
                "types": (str, datetime, ),
            },
            # Timestep used for propagation. Defaults to 60 seconds.
            "physics_step_sec": {
                "default": 60,
                "types": (int, ),
            },
            # Timestep used for propagation. Defaults to 60 seconds.
            "output_step_sec": {
                "default": 60,
                "types": (int, ),
            },
            "stop_timestamp": {
                "default": None,
                "types": (str, datetime, ),
            },
        },
        "noise": {
            # Variance of initial RSO uncertainty in filter
            "initial_error_magnitude": {
                "default": 0.00005,
                "types": (float, ),
            },
            # Type of noise to implement in dynamics propagation
            "dynamics_noise_type": {
                "default": "simple_noise",
                "types": (str, ),
            },
            # "Variance" of noise added in dynamics propagation
            "dynamics_noise_magnitude": {
                "default": 1e-20,
                "types": (float, ),
            },
            # Type of noise to implement in filter propagation
            "filter_noise_type": {
                "default": "continuous_white_noise",
                "types": (str, ),
            },
            # "Variance" of noise added in filter propagation
            "filter_noise_magnitude": {
                "default": 1e-7,
                "types": (float, ),
            },
            # RNG seed value (int|None). If `None`, use system clock
            "random_seed": {
                "default": 1,
                "types": (int, type(None),),
            },
        },
        "reward": {
            "name": {
                "default": None,
                "types": (str, ),
            },
            "metrics": {
                "default": None,
                "types": (list, ),
            },
            "parameters": {
                "default": dict(),
                "types": (dict, ),
            },
        },
        "decision": {
            "name": {
                "default": None,
                "types": (str, ),
            },
            "parameters": {
                "default": dict(),
                "types": (dict, ),
            },
        },
        "propagation": {
            # Model with which to propagate RSOs
            "propagation_model": {
                "default": "special_perturbations",
                "types": (str, ),
            },
            # Method with which to numericall integrate RSOs
            "integration_method": {
                "default": "RK45",
                "types": (str, ),
            },
            # Whether to use the internal propgation for the truth model
            "realtime_propagation": {
                "default": False,
                "types": (bool, ),
            },
            # Whether to generate observations during the simulation
            "realtime_observation": {
                "default": True,
                "types": (bool, ),
            },
        },
        "geopotential": {
            # Model file used to define the Earth's gravity model
            "model": {
                "default": "egm96.txt",
                "types": (str, ),
            },
            # Degree of the Earth's gravity model
            "degree": {
                "default": 4,
                "types": (int, ),
            },
            # Order of the Earth's gravity model
            "order": {
                "default": 4,
                "types": (int, ),
            },
        },
        "perturbations": {
            # Third bodies to include in physics model
            "third_bodies": {
                "default": [],
                "types": (list, )
            }
        },
        "target_events": {},
        "sensor_events": {},
        "targets": [],
        "sensors": [],
    }
    """dict: defines the default values for each optional :class:`.Scenario` config."""

    REQUIRED_SECTIONS = [
        "time", "reward", "decision", "targets", "sensors",
    ]
    """list: defines the required sections for the :class:`.Scenario` config."""

    OPTIONAL_SECTIONS = [
        "noise", "propagation", "geopotential", "perturbations", "target_events", "sensor_events",
    ]
    """list: defines the optional sections for the :class:`.Scenario` config."""

    def __init__(self, configuration):
        """Instantiate a :class:`.ScenarioConfig` object from a dictionary.

        Args:
            configuration (dict): config dictionary specifying :class:`.Scenario` attributes

        Raises:
            KeyError: raised if missing a required config section
            KeyError: raised if missing a required config field
            TypeError: raised if a config field has the wrong type
        """
        # Create logger for convenience
        logger = getLogger("resonaate")

        # Required config sections
        missing_section = self._checkRequiredSections(configuration)
        if missing_section:
            logger.error("Missing required section '{0}' in the Scenario config".format(
                missing_section
            ))
            raise KeyError(missing_section)

        # Performs check on all required fields
        missing_key = self._checkRequiredFields(configuration)
        if missing_key:
            logger.error("Missing required key '{0}' in '{1}' section of Scenario config".format(
                missing_key[1], missing_key[0]
            ))
            raise KeyError(missing_key[1])

        # If optional sections don't exist, add them, then add in optional fields.
        configuration = self._checkOptionalSections(configuration)
        configuration = self._checkOptionalFields(configuration)

        # Check the types of all the config fields
        bad_type = self._checkConfigTypes(configuration)
        if bad_type:
            logger.error("Incorrect type '{0}' in the Scenario config for key '{1}' = '{2}'".format(
                bad_type[2],
                bad_type[0],
                bad_type[1]
            ))
            raise TypeError(bad_type[2])

        # Grab all the sections out of the config
        self.time = configuration.pop("time")
        self.reward = configuration.pop("reward")
        self.decision = configuration.pop("decision")
        self.noise = configuration.pop("noise")
        self.propagation = configuration.pop("propagation")
        self.geopotential = configuration.pop("geopotential")
        self.perturbations = configuration.pop("perturbations")
        self.targets = configuration.pop("targets")
        self.sensors = configuration.pop("sensors")

        # Optional config sections with no defaults
        self.target_events = configuration.pop("target_events", {})
        self.sensor_events = configuration.pop("sensor_events", {})

        # Log a warning if unused sections were included in the :class:`.Scenario` config
        if configuration:
            logger.warning(
                "Scenario config included un-implemented sections: {0}".format(configuration.keys())
            )

    def _checkRequiredSections(self, configuration):
        """Check for all required config sections.

        Args:
            configuration (dict): :class:`.Scenario` config

        Returns:
            None|str: either the missing section, or None if all are present
        """
        # Grab each required config section
        for section in self.REQUIRED_SECTIONS:
            # Return the section if it wasn't included
            if section not in configuration:
                return section
        return None

    def _checkRequiredFields(self, configuration):
        """Check for all required fields of the config sections.

        Args:
            configuration (dict): :class:`.Scenario` config

        Returns:
            tuple|None: either the missing field & corresponding section or `None` if all required fields are present
        """
        # Grab each config section and all the fields
        for section, fields in self.CONFIG.items():
            if section in ("targets", "sensors"):
                continue
            # Grab each field in a section, and that field's config
            for field, field_config in fields.items():
                # Return the missing field & it's section
                if field_config["default"] is None and field not in configuration[section]:
                    return section, field
        return None

    def _checkOptionalSections(self, configuration):
        """Check for missing optional config sections.

        Args:
            configuration (dict): :class:`.Scenario` config

        Returns:
            dict: updated :class:`.Scenario` config with missing sections
        """
        # Grab each optional config section
        for section in self.OPTIONAL_SECTIONS:
            # Add the entire default section if it wasn't included
            if section not in configuration:
                # Build the entire default section
                default_section = {}
                for field, field_config in self.CONFIG[section].items():
                    default_section[field] = field_config["default"]
                # Add the default section to the configuration
                configuration[section] = default_section
        return configuration

    def _checkOptionalFields(self, configuration):
        """Check for missing optional config fields.

        Args:
            configuration (dict): :class:`.Scenario` config

        Returns:
            dict: updated :class:`.Scenario` config with missing fields
        """
        # Grab each config section and all the fields
        for section, fields in self.CONFIG.items():
            if section in ("targets", "sensors"):
                continue
            # Grab each field in a section, and that field's config
            for field, field_config in fields.items():
                # Pass on required fields
                if field_config["default"] is None:
                    continue
                # Only add a field if it's missing
                if field not in configuration[section]:
                    configuration[section][field] = field_config["default"]
        return configuration

    def _checkConfigTypes(self, configuration):
        """Check for the correct types for all config values.

        Args:
            configuration (dict): :class:`.Scenario` config

        Returns:
            tuple|None: either the missing field, value, & type or `None` all types are correct
        """
        # Grab each config section and all the fields
        for section, fields in self.CONFIG.items():
            if section in ("targets", "sensors"):
                if not isinstance(configuration[section], type(fields)):
                    return section, fields, type(fields)
                else:
                    continue
            # Grab each field in a section, and that field's config
            for field, field_config in fields.items():
                # Grab the correct type and the given value
                correct_types = field_config["types"]
                field_to_check = configuration[section][field]
                # Require the given value be of the correct type(s)
                if not isinstance(field_to_check, correct_types):
                    return field, field_to_check, type(field_to_check)
        return None
