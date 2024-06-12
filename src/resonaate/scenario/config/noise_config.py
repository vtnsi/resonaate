"""Submodule defining the 'noise' configuration section."""

from __future__ import annotations

# Standard Library Imports
from typing import Literal, Union

# Third Party Imports
from pydantic import BaseModel, Field, field_validator

# Local Imports
from ...common.labels import NoiseLabel

DEFAULT_RANDOM_SEED_VALUE: str = "os"
"""str: Allowable string value for :attr:`.NoiseConfig.random_seed`.

TODO:
    Is this still actually necessary? I'm not really sure why it's needed.
"""


class NoiseConfig(BaseModel):
    """Configuration section defining several noise-based options."""

    init_position_std_km: float = Field(default=1e-3, gt=0.0)
    """``float``: Standard deviation of initial RSO position estimate (km)."""

    init_velocity_std_km_p_sec: float = Field(default=1e-6, gt=0.0)
    """``float``: Standard deviation of initial RSO velocity estimate (km/sec)."""

    filter_noise_type: NoiseLabel = NoiseLabel.CONTINUOUS_WHITE_NOISE
    """``str``: String describing noise used in filter propagation."""

    filter_noise_magnitude: float = Field(default=3e-14, gt=0.0)
    """``float``: 'Variance' of noise added in filter propagation."""

    random_seed: Union[Literal["os"], int, None] = DEFAULT_RANDOM_SEED_VALUE
    """``str | int | None``: Pseudo-random number generator (PRNG) seed value.

    Setting this value to :attr:`.RNG_SEED_OS` will seed the PRNG with the OS's entropy.
    """

    @field_validator('random_seed')
    @classmethod
    def parse_os(cls, v) -> int | None:
        """If :attr:`.random_seed` is set to 'os', default the parsed value to ``None``.
        
        Args:
            v (str | int | None): Un-validated value of :attr:`.random_seed`.

        Returns:
            int | None: Semi-validated value of :attr:`.random_seed`.
        """
        if v == DEFAULT_RANDOM_SEED_VALUE:
            v = None
        return v
