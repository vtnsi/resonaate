"""Define MMAE initialization algorithms."""

from __future__ import annotations

# Standard Library Imports
from typing import TYPE_CHECKING

# Local Imports
from ...common.labels import InitialOrbitDeterminationLabel
from ...physics.orbit_determination.lambert import lambertBattin, lambertGauss, lambertUniversal

# Type Checking Imports
if TYPE_CHECKING:
    # Local Imports
    from ...physics.orbit_determination import OrbitDeterminationFunction


_LAMBERT_IOD_MAP: dict[str, OrbitDeterminationFunction] = {
    InitialOrbitDeterminationLabel.LAMBERT_BATTIN: lambertBattin,
    InitialOrbitDeterminationLabel.LAMBERT_GAUSS: lambertGauss,
    InitialOrbitDeterminationLabel.LAMBERT_UNIVERSAL: lambertUniversal,
}


def lambertInitializationFactory(name: str) -> OrbitDeterminationFunction:
    """Build a lambert class for use in initial orbit determination.

    Args:
        name (``str``): name of orbit determination method.

    Returns:
        :func:`.OrbitDeterminationFunction`: orbit determination function.
    """
    if not name:
        return None
    if name.lower() in _LAMBERT_IOD_MAP:
        iod_class = _LAMBERT_IOD_MAP[name]
    else:
        raise ValueError(f"Invalid Initial Orbit Determination type: {name}")

    return iod_class
