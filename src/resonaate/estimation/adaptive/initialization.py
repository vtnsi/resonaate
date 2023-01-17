"""Define MMAE initialization algorithms."""
from __future__ import annotations

# Standard Library Imports
from typing import TYPE_CHECKING

# Local Imports
from ...physics.orbit_determination.lambert import lambertBattin, lambertGauss, lambertUniversal

# Type Checking Imports
if TYPE_CHECKING:
    # Local Imports
    from ...physics.orbit_determination import OrbitDeterminationFunction


LAMBERT_BATTIN_LABEL = "lambert_battin"
"""``str``: Constant string used to describe Lambert Battin function."""

LAMBERT_GAUSS_LABEL = "lambert_gauss"
"""``str``: Constant string used to describe Lambert Gauss function."""

LAMBERT_UNIVERSAL_LABEL = "lambert_universal"
"""``str``: Constant string used to describe Lambert universal function."""

_LAMBERT_IOD_MAP: dict[str, OrbitDeterminationFunction] = {
    LAMBERT_BATTIN_LABEL: lambertBattin,
    LAMBERT_GAUSS_LABEL: lambertGauss,
    LAMBERT_UNIVERSAL_LABEL: lambertUniversal,
}

VALID_LAMBERT_IOD_LABELS: tuple[str] = tuple(_LAMBERT_IOD_MAP.keys())
"""``tuple[str]``: Valid entries for :py:data:`'orbit_determination'` key in iod configuration."""


def lambertInitializationFactory(name: str) -> OrbitDeterminationFunction:
    """Build a lambert class for use in initial orbit determination.

    Args:
        name (``str``): name of orbit determination method.

    Returns:
        :func:`.OrbitDeterminationFunction`: orbit determination function.
    """
    if not name:
        return None
    if name.lower() in VALID_LAMBERT_IOD_LABELS:
        iod_class = _LAMBERT_IOD_MAP[name]
    else:
        raise ValueError(name)

    return iod_class
