"""Package that defines agent-based simulation behavior."""


DEFAULT_MASS = 10000.0
"""``float``: Default mass of non-spacecraft (kg)  #.  :cite:t:`LEO_RSO_2022_stats`"""
LEO_DEFAULT_MASS = 295.0
"""``float``: Default mass of LEO RSO (kg)  #.  :cite:t:`LEO_RSO_2022_stats`"""
MEO_DEFAULT_MASS = 2861.0
"""``float``: Default mass of MEO RSO (kg)  #.  :cite:t:`steigenberger_MEO_RSO_2022_stats`"""
GEO_DEFAULT_MASS = 6200.0
"""``float``: Default mass of GEO RSO (kg)  #.  :cite:t:`GEO_RSO_2022_stats`"""

DEFAULT_VCS = 400.0
"""``float``: Default visual cross section of 20m by 20m building (m^2)."""
LEO_DEFAULT_VCS = 10.0
"""``float``: Default visual cross section of LEO RSO (m^2)  #.  :cite:t:`LEO_RSO_2022_stats`"""
MEO_DEFAULT_VCS = 37.5
"""``float``: Default visual cross section of MEO RSO (m^2)  #.  :cite:t:`steigenberger_MEO_RSO_2022_stats`"""
GEO_DEFAULT_VCS = 90.0
"""``float``: Default visual cross section of GEO RSO (m^2)  #.  :cite:t:`GEO_RSO_2022_stats`"""

SOLAR_PANEL_REFLECTIVITY: float = 0.21
"""``float``: reflectivity of a solar panel :cite:t:`montenbruck_2012_orbits`, unit-less."""
