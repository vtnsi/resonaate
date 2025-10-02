"""Subpackage defining how a :class:`.Scenario` can be configured."""

from __future__ import annotations

# Standard Library Imports
import os.path
from typing import TYPE_CHECKING

# Third Party Imports
from pydantic import BaseModel, Field, create_model

# Local Imports
from ...common.utilities import loadJSONFile
from .agent_config import AgentConfig, SensingAgentConfig
from .engine_config import SENSOR_FIELD_ALIAS, TARGET_FIELD_ALIAS, EngineConfig
from .estimation_config import EstimationConfig
from .event_configs import EventConfig
from .geopotential_config import GeopotentialConfig
from .noise_config import NoiseConfig
from .observation_config import ObservationConfig
from .perturbations_config import PerturbationsConfig
from .propagation_config import PropagationConfig
from .sensor_config import (
    AdvRadarConfig,
    ConicFieldOfViewConfig,
    FieldOfViewConfig,
    OpticalConfig,
    RadarConfig,
    RectangularFieldOfViewConfig,
    ScheduledDowntimeConfig,
    SensorConfig,
)
from .time_config import TimeConfig

# Type Checking Imports
if TYPE_CHECKING:
    # Standard Library Imports
    from collections.abc import Callable
    from pathlib import Path
    from typing import Any


__all__ = [  # noqa: RUF022, RUF100
    "ScenarioConfig",
    "ConfigObject",
    "ConfigObjectList",
    "SensingAgentConfig",
    "AgentConfig",
    "EngineConfig",
    "EstimationConfig",
    "EventConfig",
    "EventConfigList",
    "GeopotentialConfig",
    "NoiseConfig",
    "ObservationConfig",
    "PerturbationsConfig",
    "PropagationConfig",
    "TimeConfig",
    "ScheduledDowntimeConfig",
    "SensorConfig",
    "FieldOfViewConfig",
    "ConicFieldOfViewConfig",
    "RectangularFieldOfViewConfig",
    "OpticalConfig",
    "RadarConfig",
    "AdvRadarConfig",
]

# Some constants that define various mutated fields in the config that get parsed, popped, then processed.
# They're not actually in the ScenarioConfig object, but they're defined here so it's not magic string literals

ENGINES_FILES_FIELD: str = "engines_files"
"""``str``: Name of the main init config field where the user provides a list of engine config files."""

TARGETS_FILE_FIELD: str = "targets_file"
"""``str``: Name of the engine init file config field where the user specifies the path to the targets file."""

SENSORS_FILE_FIELD: str = "sensors_file"
"""``str``: Name of the engine init file config field where the user specifies the path to the sensors file."""

EVENT_FILES_FIELD: str = "event_files"
"""``str``: Name of the main initi config field where the user provides a list of event files. Note that this \
extends the list of events as configured under the existing `events` field, theses events are appended to the total list."""

ENGINE_LIST_ALIAS: str = "engines"
"""``str``: Name of the engine list. Should be aliased to match the field in :class:`.ScenarioConfig`'s `engines` field."""

EVENT_LIST_ALIAS: str = "events"
"""``str``: Name of the events list. Should be aliased to match the field in :class:`.ScenarioCOnfig`'s `events` field."""


class ScenarioConfig(BaseModel):
    """Configuration class for creating valid :class:`.Scenario` objects.

    This allows the extra logic for properly checking all configs to be abstracted from the
    factory methods and the :class:`.Scenario`'s constructor.
    """

    time: TimeConfig
    """:class:`.TimeConfig`: simulation time configuration object, **required**."""

    estimation: EstimationConfig
    """:class:`.EstimationConfig`: estimation & filtering configuration object, **required**."""
    # NOTE: This is aliased because the field name string key is referenced directly in config parsing.
    engines: list[EngineConfig] = Field(
        ...,
        alias=ENGINE_LIST_ALIAS,
    )  # NOTE: This is aliased because the field name string key is referenced directly in config parsing.
    """:class:`.ConfigObjectList`: list of :class:`.EngineConfig` objects to use for tasking, **required**."""

    noise: NoiseConfig = NoiseConfig()
    """:class:`.NoiseConfig`: noise types and values to in the simulation."""

    propagation: PropagationConfig = PropagationConfig()
    """:class:`.PropagationConfig`: define propagation techniques used during simulation."""

    geopotential: GeopotentialConfig = GeopotentialConfig()
    """:class:`.GeopotentialConfig`: define the geopotential model of the Earth to use in the :class:`.SpecialPerturbations` propagator."""

    perturbations: PerturbationsConfig = PerturbationsConfig()
    """:class:`.PerturbationsConfig`: define perturbations to include in the :class:`.SpecialPerturbations` propagator."""

    observation: ObservationConfig = ObservationConfig()
    """:class:`.ObservationConfig`: configurations specific to observation behavior."""

    events: list[EventConfig] = Field(
        default_factory=list,
        alias=EVENT_LIST_ALIAS,
    )  # NOTE: This is aliased because the field name string key is referenced directly in config parsing.
    """`list[EventConfig]`: List of :class:`EventConfig` configured in the scenario."""

    @classmethod
    def fromConfigFile(cls, config_file_path: str | Path) -> ScenarioConfig:
        """Parse a configuration file and generate a :class:`.ScenarioConfig` from it.

        Args:
            config_file_path (``str``): Path to initialization configuration file.

        Returns:
            :class:`.ScenarioConfig`: Generated from configuration file.
        """
        config_dict = cls.parseConfigFile(config_file_path)
        return cls(**config_dict)

    @staticmethod
    def parseConfigFile(
        path: str | Path,
        file_loader: Callable[[str | Path], Any] = loadJSONFile,
    ) -> dict[str, Any]:
        """Parse out configuration from a given filepath. Mutates the config and parses pathing to external files.

        Args:
            path (``str``): path to main config file
            file_loader (``callable``, optional): function to load a JSON file from a given path. Defaults to
                :func:`loadJSONFile`.

        Returns:
            ``dict``: config dictionary object with the necessary fields
        """
        # Load the main config, and save the path
        config_file_path = os.path.abspath(path)
        config_directory = os.path.dirname(config_file_path)
        configuration = file_loader(config_file_path)

        # Load the Tasking Engines
        engine_files = configuration.pop(ENGINES_FILES_FIELD)
        configuration[ENGINE_LIST_ALIAS] = (
            []
        )  # This magic string literal is at least a little ok cause it's directly associated with this
        # classes' .engines attribute.
        for engine_file in engine_files:
            engine_config = file_loader(os.path.join(config_directory, engine_file))

            # Load the RSO target set
            targets = file_loader(
                os.path.join(config_directory, engine_config.pop(TARGETS_FILE_FIELD)),
            )

            # Load the sensor set
            sensors = file_loader(
                os.path.join(config_directory, engine_config.pop(SENSORS_FILE_FIELD)),
            )

            engine_config.update({TARGET_FIELD_ALIAS: targets, SENSOR_FIELD_ALIAS: sensors})
            configuration[ENGINE_LIST_ALIAS].append(engine_config)

        # Load in any optional event files.
        if EVENT_FILES_FIELD in configuration:
            if EVENT_LIST_ALIAS not in configuration:  # populate if not present
                configuration[EVENT_LIST_ALIAS] = (
                    []
                )  # Assign if it's not there cause this aint a DefaultDict.
            event_files: list[str] = configuration.pop(EVENT_FILES_FIELD)
            for event_file in event_files:
                configuration[EVENT_LIST_ALIAS].extend(
                    loadJSONFile(os.path.join(config_directory, event_file)),
                )

        return configuration


def constructFromUnion(disc_union, cfg_dict: dict) -> BaseModel:
    """Construct a concrete pydantic model from `disc_union` specified by `cfg_dict`.

    Args:
        disc_union: An Annotated Union type definition where the first argument is a Union of the
            discriminated pydantic models and the second argument is the FieldInfo that contains
            the discriminator information.
        cfg_dict: Dictionary specifying attributes of the `disc_union` being constructed.

    Returns:
        BaseModel: Concrete pydantic model chosen from discriminated union described by `disc_union`.
    """
    dummy_model = create_model("Dummy", inner=disc_union)
    dumdum = dummy_model(inner=cfg_dict)
    return dumdum.inner
