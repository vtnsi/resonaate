"""Define MMAE initialization algorithms."""
from __future__ import annotations

# Standard Library Imports
from typing import TYPE_CHECKING

# Local Imports
from ...physics.orbit_determination.lambert import lambertGauss, lambertMinEnergy, lambertUniversal

# Type Checking Imports
if TYPE_CHECKING:
    # Local Imports
    from ...physics.orbit_determination import OrbitDeterminationFunction


LAMBERT_MIN_SMA_LABEL = "lambert_min_sma"
"""``str``: Constant string used to describe Lambert minimum SMA function."""

LAMBERT_GAUSS_LABEL = "lambert_gauss"
"""``str``: Constant string used to describe Lambert Gauss function."""

LAMBERT_UNIVERSAL_LABEL = "lambert_universal"
"""``str``: Constant string used to describe Lambert universal function."""


_ORBIT_DETERMINATION_MAP: dict[str, OrbitDeterminationFunction] = {
    LAMBERT_MIN_SMA_LABEL: lambertMinEnergy,
    LAMBERT_GAUSS_LABEL: lambertGauss,
    LAMBERT_UNIVERSAL_LABEL: lambertUniversal,
}


VALID_ORBIT_DETERMINATION_LABELS: tuple[str] = tuple(_ORBIT_DETERMINATION_MAP.keys())
"""``tuple[str]``: Valid entries for :py:data:`'orbit_determination'` key in filter configuration."""


def lambertInitializationFactory(name: str) -> OrbitDeterminationFunction:
    """Build a lambert class for use in filtering.

    Args:
        name (``str``): name of orbit determination method.

    Returns:
        :func:`.OrbitDeterminationFunction`: orbit determination function.
    """
    if not name:
        return None

    if name.lower() in VALID_ORBIT_DETERMINATION_LABELS:
        iod_class = _ORBIT_DETERMINATION_MAP[name]
    else:
        raise ValueError(name)

    return iod_class
