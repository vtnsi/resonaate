"""Defines the :class:`.Earth` class."""

from __future__ import annotations


class Earth:
    """Defines the common Earth constants.

    Attributes:
        mu (``float``): gravitational parameter, (km^3/sec^2).
        radius (``float``): mean equatorial radius (km).
        mass (``float``): planet's mass, (km).
        gravity (``float``): average gravitational acceleration (m/sec^2)
        spin_rate (``float``): rotation rate about the *K*-axis (ECEF), (rad/sec).
        eccentricity (``float``): equatorial bulge, (unit-less).
        atmosphere (``float``): assumed height of the atmosphere, (km).
        j2 (``float``): second-order zonal coefficient, (unit-less).
        j3 (``float``): third-order zonal coefficient, (unit-less).
        j4 (``float``): fourth-order zonal coefficient, (unit-less).

    References:
        #. :cite:t:`vallado_2013_astro`, Appendix D.1, Table D-1
        #. :cite:t:`montenbruck_2012_orbits`
    """

    # [TODO]: Source these from a singular place/model (GGM03S?)

    # EGM-08 Zonal coefficients (normalized). Vallado Ed. 4, Appendix D.1, Table D-1. Dimensionless
    #   [NOTE]: J_i = -C_i = Cbar_i,0 / PI_i,o
    mu = 398600.4415
    radius = 6378.1363
    mass = 5.9742e24
    gravity = 9.81
    spin_rate = 7.292115146706979e-5
    eccentricity = 0.081819221456
    atmosphere = 100.0
    j2 = 1.08262617385222e-3
    j3 = -2.53241051856772e-6
    j4 = -1.61989759991697e-6
