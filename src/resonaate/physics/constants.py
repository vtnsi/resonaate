"""Global math & physics constants.

This module holds all constants that are used in various places across the
codebase, allowing for a consistent place to store them. Constants specific
to objects and classes remain in those files.

References:
    #. :cite:t:`montenbruck_2012_orbits`, Eqn 3.67
    #. :cite:t:`vallado_2013_astro`
"""

from __future__ import annotations

# Third Party Imports
from numpy import pi

# Conversion constants
PI = pi
TWOPI = 2.0 * pi
DAYS2SEC = 24.0 * 3600
SEC2DAYS = 1.0 / DAYS2SEC
DEG2RAD = pi / 180.0
RAD2DEG = 180.0 / pi
ARCSEC2DEG = 1.0 / 3600.0
ARCSEC2RAD = ARCSEC2DEG * DEG2RAD
DEG2SEC = 240
RAD2SEC = RAD2DEG * DEG2SEC
SEC2ARCSEC = 15
ARCSEC2SEC = 1 / SEC2ARCSEC
AU2KM = 1.49599 * 10**8  # Astronomical Unit to kilometer
M2KM = 1.0 / 1000.0
KM2M = 1000.0

# Physics constants
SOLAR_FLUX = 1367.0  # Solar flux at Earth's orbit, (W/m^2)
SPEED_OF_LIGHT = 2.99792458e8  # Speed of Light, (m/s)
SOLAR_PRESSURE = SOLAR_FLUX / SPEED_OF_LIGHT  # Solar Energy Density, (N/m^2), Montenbruck Eq. 3.67

SOLAR_PANEL_REFLECTIVITY: float = 0.21
"""``float``: reflectivity of a solar panel :cite:t:`montenbruck_2012_orbits`, unit-less."""
