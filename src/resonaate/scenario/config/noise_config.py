"""Submodule defining the 'noise' configuration section."""

from __future__ import annotations

# Standard Library Imports
from typing import ClassVar, Literal, Union

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

    DEFAULT_POS_STD: ClassVar[float] = 1e-3
    """``float``: Default standard deviation of initial RSO position estimate (km)."""

    init_position_std_km: float = Field(default=DEFAULT_POS_STD, gt=0.0)
    """``float``: Standard deviation of initial RSO position estimate (km)."""

    DEFAULT_VEL_STD: ClassVar[float] = 1e-6
    """``float``: Default standard deviation of initial RSO velocity estimate (km/sec)."""

    init_velocity_std_km_p_sec: float = Field(default=DEFAULT_VEL_STD, gt=0.0)
    """``float``: Standard deviation of initial RSO velocity estimate (km/sec)."""

    filter_noise_type: NoiseLabel = NoiseLabel.CONTINUOUS_WHITE_NOISE
    """``str``: String describing noise used in filter propagation."""

    DEFAULT_NOISE_MAG: ClassVar[float] = 3e-14
    """``float``: Default 'variance' of noise added in filter propagation."""

    filter_noise_magnitude: float = Field(default=DEFAULT_NOISE_MAG, gt=0.0)
    """``float``: 'Variance' of noise added in filter propagation."""

    random_seed: Union[Literal["os"], int, None] = None  # noqa: UP007
    """``str | int | None``: Pseudo-random number generator (PRNG) seed value.

    Setting this value to :attr:`.RNG_SEED_OS` will seed the PRNG with the OS's entropy.
    """

    @field_validator("random_seed")
    @classmethod
    def validate_seed(cls, v) -> int | None:
        """Parse :attr:`.random_seed` and validate its value.

        Args:
            v (str | int | None): Un-validated value of :attr:`.random_seed`.

        Returns:
            int | None: Valid value of :attr:`.random_seed`.

        Raises:
            AssertionError: If `v` is not a valid value.
        """
        if v == DEFAULT_RANDOM_SEED_VALUE:
            return None

        if not isinstance(v, int):
            raise ValueError(f"Specified seed value not 'os' or valid integer: {v}")
        if v < 0:
            raise ValueError(f"Invalid specified seed value: {v}")
        return v
