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
from .engine_config import EngineConfig
from .estimation_config import EstimationConfig
from .event_configs import EventConfig
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
]


class ScenarioConfig(BaseModel):
    """Configuration class for creating valid :class:`.Scenario` objects.

    This allows the extra logic for properly checking all configs to be abstracted from the
    factory methods and the :class:`.Scenario`'s constructor.
    """

    time: TimeConfig
    """:class:`.TimeConfig`: simulation time configuration object, **required**."""

    estimation: EstimationConfig
    """:class:`.EstimationConfig`: estimation & filtering configuration object, **required**."""

    engines: list[EngineConfig]
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

    events: list[EventConfig] = Field(default_factory=list)
    """list[EventConfigList]: list of :class:`.EventConfig` objects that occur during the simulation."""

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
                os.path.join(config_directory, engine_config.pop("targets_file")),
            )

            # Load the sensor set
            sensors = file_loader(
                os.path.join(config_directory, engine_config.pop("sensors_file")),
            )

            engine_config.update({"targets": targets, "sensors": sensors})
            configuration["engines"].append(engine_config)

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
