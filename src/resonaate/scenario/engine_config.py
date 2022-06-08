# Standard Library Imports
from logging import getLogger
# Third Party Imports
# RESONAATE Imports


class EngineConfig:
    """Configuration class for creating valid :class:`.Engines`s.

    This allows the extra logic for properly checking all configs to be abstracted from the
    factory methods and the :class:`.Engine`'s constructor.
    """

    CONFIG = {
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
        "target_set": [],
        "sensor_set": [],
    }
    """dict: defines the default values for each optional :class:`.Scenario` config."""

    REQUIRED_SECTIONS = [
        "reward", "decision", "target_set", "sensor_set",
    ]
    """list: defines the required sections for the :class:`.Scenario` config."""

    OPTIONAL_SECTIONS = []
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

        # Check the types of all the config fields
        bad_type = self._checkConfigTypes(configuration)
        if bad_type:
            logger.error("Incorrect type '{0}' in the Scenario config for key '{1}' = '{2}'".format(
                bad_type[2],
                bad_type[0],
                bad_type[1]
            ))
            raise TypeError(bad_type[2])

        self.reward = configuration.pop("reward")
        self.decision = configuration.pop("decision")
        self.targets = configuration.pop("targets")
        self.sensor_networks = configuration.pop("sensor_networks")
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
            # if section in ("engine", "filter"):
            #     continue
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

    def _checkConfigTypes(self, configuration):
        """Check for the correct types for all config values.

        Args:
            configuration (dict): :class:`.Scenario` config

        Returns:
            tuple|None: either the missing field, value, & type or `None` all types are correct
        """
        # Grab each config section and all the fields
        for section, fields in self.CONFIG.items():
            if section in ("reward", "decision"):
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
