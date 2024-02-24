"""Submodule defining the 'geopotential' configuration section."""

from __future__ import annotations

# Standard Library Imports
from dataclasses import dataclass
from typing import ClassVar

# Local Imports
from .base import ConfigObject, ConfigValueError, inclusiveRange

VALID_GEOPOTENTIAL_MODELS: tuple[str] = (
    "egm2008.txt",
    "egm96.txt",
    "GGM03S.txt",
    "jgm3.txt",
)
DEFAULT_GRAVITY_MODEL: str = "egm96.txt"
DEFAULT_GRAVITY_DEGREE: int = 4
DEFAULT_GRAVITY_ORDER: int = 4
MAX_GRAVITY_DEGREE: int = 80
MAX_GRAVITY_ORDER: int = 80


@dataclass
class GeopotentialConfig(ConfigObject):
    """Configuration section defining several geopotential-based options."""

    CONFIG_LABEL: ClassVar[str] = "geopotential"
    """``str``: Key where settings are stored in the configuration dictionary."""

    model: str = DEFAULT_GRAVITY_MODEL
    """``str``: Model file used to define the Earth's gravity model."""

    degree: int = DEFAULT_GRAVITY_DEGREE
    """``int``: Degree of the Earth's gravity model."""

    order: int = DEFAULT_GRAVITY_ORDER
    """``int``: Order of the Earth's gravity model."""

    def __post_init__(self):
        """Runs after the object is initialized."""
        if self.model not in VALID_GEOPOTENTIAL_MODELS:
            raise ConfigValueError("model", self.model, VALID_GEOPOTENTIAL_MODELS)

        if self.degree not in inclusiveRange(MAX_GRAVITY_DEGREE):
            raise ConfigValueError("degree", self.degree, inclusiveRange(MAX_GRAVITY_DEGREE))

        if self.order not in inclusiveRange(MAX_GRAVITY_DEGREE):
            raise ConfigValueError("order", self.order, inclusiveRange(MAX_GRAVITY_ORDER))
