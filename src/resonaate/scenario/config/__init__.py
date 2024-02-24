"""Subpackage defining how a :class:`.Scenario` can be configured."""

from __future__ import annotations

# Standard Library Imports
import os.path
from dataclasses import dataclass, field, fields
from typing import TYPE_CHECKING, ClassVar

# Local Imports
from ...common.utilities import loadJSONFile
from .agent_config import SensingAgentConfig, TargetAgentConfig
from .base import ConfigObject, ConfigObjectList
from .engine_config import EngineConfig
from .estimation_config import EstimationConfig
from .event_configs import EventConfig, EventConfigList
from .geopotential_config import GeopotentialConfig
from .noise_config import NoiseConfig
from .observation_config import ObservationConfig
from .perturbations_config import PerturbationsConfig
from .propagation_config import PropagationConfig
from .time_config import TimeConfig

# Type Checking Imports
if TYPE_CHECKING:
    # Standard Library Imports
    from collections.abc import Callable
    from pathlib import Path
    from typing import Any


__all__ = [
    "ScenarioConfig",
    "ConfigObject",
    "ConfigObjectList",
    "SensingAgentConfig",
    "TargetAgentConfig",
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
]


@dataclass
class ScenarioConfig(ConfigObject):
    """Configuration class for creating valid :class:`.Scenario` objects.

    This allows the extra logic for properly checking all configs to be abstracted from the
    factory methods and the :class:`.Scenario`'s constructor.
    """

    time: TimeConfig | dict
    """:class:`.TimeConfig`: simulation time configuration object, **required**."""

    estimation: EstimationConfig | dict
    """:class:`.EstimationConfig`: estimation & filtering configuration object, **required**."""

    engines: ConfigObjectList[EngineConfig] | list[EngineConfig | dict]
    """:class:`.ConfigObjectList`: list of :class:`.EngineConfig` objects to use for tasking, **required**."""

    noise: NoiseConfig | dict | None = None
    """:class:`.NoiseConfig`: noise types and values to in the simulation."""

    propagation: PropagationConfig | dict | None = None
    """:class:`.PropagationConfig`: define propagation techniques used during simulation."""

    geopotential: GeopotentialConfig | dict | None = None
    """:class:`.GeopotentialConfig`: define the geopotential model of the Earth to use in the :class:`.SpecialPerturbations` propagator."""

    perturbations: PerturbationsConfig | dict | None = None
    """:class:`.PerturbationsConfig`: define perturbations to include in the :class:`.SpecialPerturbations` propagator."""

    observation: ObservationConfig | dict | None = None
    """:class:`.ObservationConfig`: configurations specific to observation behavior."""

    events: EventConfigList[EventConfig] | list[EventConfig | dict] = field(default_factory=list)
    """:class:`.EventConfigList`: list of :class:`.EventConfig` objects that occur during the simulation."""

    OPTIONAL_SECTION_MAP: ClassVar[dict[str, ConfigObject]] = {
        "noise": NoiseConfig,
        "propagation": PropagationConfig,
        "geopotential": GeopotentialConfig,
        "perturbations": PerturbationsConfig,
        "observation": ObservationConfig,
    }
    """``dict``: mapping that makes auto-validating optional sub-configs easier."""

    def __post_init__(self) -> None:  # noqa: C901
        """Runs after the object is initialized."""
        # Required sections
        if isinstance(self.time, dict):
            self.time = TimeConfig(**self.time)

        if isinstance(self.estimation, dict):
            self.estimation = EstimationConfig(**self.estimation)

        if isinstance(self.engines, list):
            self.engines = ConfigObjectList("engines", EngineConfig, self.engines)

        if isinstance(self.events, list):
            self.events = EventConfigList("events", EventConfig, self.events, default_empty=True)

        # Optional sub-config sections
        for section in fields(self):
            if getattr(self, section.name) is None:
                setattr(self, section.name, self.OPTIONAL_SECTION_MAP[section.name]())

        if isinstance(self.noise, dict):
            self.noise = NoiseConfig(**self.noise)

        if isinstance(self.propagation, dict):
            self.propagation = PropagationConfig(**self.propagation)

        if isinstance(self.geopotential, dict):
            self.geopotential = GeopotentialConfig(**self.geopotential)

        if isinstance(self.perturbations, dict):
            self.perturbations = PerturbationsConfig(**self.perturbations)

        if isinstance(self.observation, dict):
            self.observation = ObservationConfig(**self.observation)

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
        """Parse out configuration from a given filepath.

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
        engine_files = configuration.pop("engines_files")
        configuration["engines"] = []
        for engine_file in engine_files:
            engine_config = file_loader(os.path.join(config_directory, engine_file))

            # Load the RSO target set
            targets = file_loader(
                os.path.join(config_directory, engine_config.pop("targets_file"))
            )

            # Load the sensor set
            sensors = file_loader(
                os.path.join(config_directory, engine_config.pop("sensors_file"))
            )

            engine_config.update({"targets": targets, "sensors": sensors})
            configuration["engines"].append(engine_config)

        return configuration
