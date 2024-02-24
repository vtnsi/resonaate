"""Submodule defining the 'noise' configuration section."""

from __future__ import annotations

# Standard Library Imports
from dataclasses import dataclass
from typing import ClassVar

# Local Imports
from ...common.labels import NoiseLabel
from .base import ConfigObject, ConfigTypeError, ConfigValueError

DEFAULT_RANDOM_SEED_VALUE: str = "os"
"""``str``: Value to set :attr:`~.NoiseConfig.random_seed` to that indicates seeding the PRNG with the OS's entropy."""

VALID_NOISE_TYPES: tuple[str] = (
    NoiseLabel.CONTINUOUS_WHITE_NOISE,
    NoiseLabel.DISCRETE_WHITE_NOISE,
    NoiseLabel.SIMPLE_NOISE,
)
"""``tuple``: Valid noise types."""


DEFAULT_POSITION_STD: float = 1e-3
"""``float``: Default value for :attr:`~.NoiseConfig.init_position_std_km`."""

DEFAULT_VELOCITY_STD: float = 1e-6
"""``float``: Default value for :attr:`~.NoiseConfig.init_velocity_std_km_p_sec`."""

DEFAULT_FILTER_NOISE_MAGNITUDE: float = 3e-14
"""``float``: Default value for :attr:`~.NoiseConfig.filter_noise_magnitude`."""


@dataclass
class NoiseConfig(ConfigObject):
    """Configuration section defining several noise-based options."""

    CONFIG_LABEL: ClassVar[str] = "noise"
    """``str``: Key where settings are stored in the configuration dictionary."""

    init_position_std_km: float = DEFAULT_POSITION_STD
    """``float``: Standard deviation of initial RSO position estimate (km)."""

    init_velocity_std_km_p_sec: float = DEFAULT_VELOCITY_STD
    """``float``: Standard deviation of initial RSO velocity estimate (km/sec)."""

    filter_noise_type: str = NoiseLabel.CONTINUOUS_WHITE_NOISE
    """``str``: String describing noise used in filter propagation."""

    filter_noise_magnitude: float = DEFAULT_FILTER_NOISE_MAGNITUDE
    """``float``: 'Variance' of noise added in filter propagation."""

    random_seed: str | int | None = DEFAULT_RANDOM_SEED_VALUE
    """``str | int | None``: Pseudo-random number generator (PRNG) seed value.

    Setting this value to :attr:`.RNG_SEED_OS` will seed the PRNG with the OS's entropy.
    """

    def __post_init__(self):
        """Initialize :attr:`~.NoiseConfig.random_seed`."""
        if isinstance(self.random_seed, str):
            if self.random_seed != DEFAULT_RANDOM_SEED_VALUE:
                raise ConfigValueError(
                    "random_seed",
                    self.random_seed,
                    (DEFAULT_RANDOM_SEED_VALUE, None, "or any positive int"),
                )
            self.random_seed = None

        elif not isinstance(self.random_seed, int):
            raise ConfigTypeError(
                "random_seed",
                self.random_seed,
                (DEFAULT_RANDOM_SEED_VALUE, None, "or any positive int"),
            )

        elif self.random_seed < 0:
            raise ConfigValueError(
                "random_seed",
                self.random_seed,
                (DEFAULT_RANDOM_SEED_VALUE, None, "or any positive int"),
            )

        if self.filter_noise_type not in VALID_NOISE_TYPES:
            raise ConfigValueError("filter_noise_type", self.filter_noise_type, VALID_NOISE_TYPES)

        if self.filter_noise_magnitude <= 0.0:
            raise ConfigValueError("filter_noise_magnitude", self.filter_noise_magnitude, "> 0.0")

        if self.init_position_std_km <= 0.0:
            raise ConfigValueError("init_position_std_km", self.init_position_std_km, "> 0.0")

        if self.init_velocity_std_km_p_sec <= 0.0:
            raise ConfigValueError(
                "init_velocity_std_km_p_sec", self.init_velocity_std_km_p_sec, "> 0.0"
            )
