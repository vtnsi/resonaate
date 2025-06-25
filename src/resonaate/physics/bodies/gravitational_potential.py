"""Module for defining the nonspherical gravity potential of a central body being orbited by an object."""

from __future__ import annotations

# Standard Library Imports
from csv import reader
from functools import lru_cache
from importlib import resources
from math import factorial
from typing import TYPE_CHECKING

# Third Party Imports
from numpy import array, float64, sqrt, zeros
from scipy.linalg import norm

# Type Checking Imports
if TYPE_CHECKING:
    # Third Party Imports
    from numpy import ndarray

    # Local Imports
    from ...common.labels import GeopotentialModel


GEOPOTENTIAL_MODULE: str = "resonaate.physics.data.geopotential"
"""``str``: defines geopotential data module location."""


@lru_cache(maxsize=5)
def loadGeopotentialCoefficients(gravity_model: GeopotentialModel) -> tuple[ndarray, ndarray]:
    r"""Read the gravity model file & save the geopotential coefficients.

    This assumes that the coefficients are normalized according to Eq 8-22 in Vallado:

    :math:`\bar{S}_{n,m}=\Pi_{n,m} S_{n,m}`
    :math:`\bar{C}_{n,m}=\Pi_{n,m} C_{n,m}`

    where the function returns :math:`S_{n,m}` and :math:`C_{n,m}` accordingly.

    References:
        :cite:t:`vallado_2013_astro`, Eqn 8-22, Pg 546

    Args:
        gravity_model (:class:`.GeopotentialModel`): Enum instance of the geopotential model.

    Returns:
        ``tuple``: ``ndarray`` defining the un-normalized cosine & sine geopotential coefficients.
    """
    res = resources.files(GEOPOTENTIAL_MODULE).joinpath(gravity_model.value)
    with resources.as_file(res) as grv_filepath, open(grv_filepath, encoding="utf-8") as csv_file:
        cos_terms = zeros((181, 181))
        sin_terms = zeros((181, 181))
        for row in reader(csv_file, delimiter=" ", skipinitialspace=True):
            # Read normalized coefficients, un-normalize them.
            degree, order = int(row[0]), int(row[1])
            scale = _getGeopotentialCoefficientScale(degree, order)
            cos_terms[degree, order] = float(row[2]) * scale
            sin_terms[degree, order] = float(row[3]) * scale

    return cos_terms, sin_terms


def _getGeopotentialCoefficientScale(degree: int, order: int) -> float:
    r"""Get the scale to un-normalize the corresponding geopotential coefficients.

    :math:`\Pi_{n,m} = \sqrt{\frac{(n + m)!}{(n - m)!k(2n + 1)}}` where
    :math:`k=1` if :math:`m=0`
    :math:`k=2` if :math:`m \neq 0`

    References:
        :cite:t:`vallado_2013_astro`, Eqn 8-22, Pg 546

    Args:
        degree (``int``): geopotential coefficient degree.
        order (``int``): geopotential coefficient order.

    Returns:
        ``float``: un-normalization scale value.
    """
    if order == 0:
        return sqrt(2 * degree + 1)

    return sqrt((factorial(degree - order) * 2 * (2 * degree + 1)) / factorial(degree + order))


def getNonSphericalHarmonics(
    ecef_pos: ndarray,
    cb_radius: float,
    degree: int,
    order: int,
) -> tuple[ndarray, ndarray]:
    r"""Compute the harmonic terms for a given position & gravity field.

    Note:
        The gravity model order must be less than or equal to the gravity model degree.
        This function only considers J2 and above. It does not include Keplerian Force Accelerations.

    References:
        :cite:t:`montenbruck_2012_orbits`, Eqn 3.29 - 3.31

    Args:
        ecef_pos (``ndarray``): ITRF/ECEF for which to calculate harmonic terms (km).
        cb_radius (``float``): spherical radius of the central body (km).
        degree (``int``): maximum degree (:math:`n`) of the gravity model.
        order (``int``): maximum order (:math:`m`) of the gravity model.

    Returns:
        ``ndarray``: (n+1 x m+1) matrix of recursive cosine harmonic terms.
        ``ndarray``: (n+1 x m+1) matrix of recursive sine harmonic terms.
    """
    # Temporary variables for convenience
    norm_r = norm(ecef_pos)
    rho = cb_radius / norm_r
    rho_sq = rho**2
    # Normalize the ITRF/ECEF coordinates
    [x_bar, y_bar, z_bar] = ecef_pos * rho / norm_r

    # Initialize & pre-compute the harmonics terms
    v = zeros((degree + 1, order + 1), dtype=float64)
    w = zeros((degree + 1, order + 1), dtype=float64)

    v[0, 0] = rho
    v[1, 0] = z_bar * v[0, 0]
    v[1, 1] = x_bar * v[0, 0]
    w[1, 1] = y_bar * v[0, 0]

    # Harmonic term recurrence relations defined in "Satellite Orbits" by Montenbruck (3.29 - 3.31)
    for m in range(order + 1):
        for n in range(2, degree + 1):
            # Skip terms above the diagonal
            if m > n:
                continue
            # Diagonal terms
            if m == n:
                v[m, m] = (2 * m - 1) * (x_bar * v[m - 1, m - 1] - y_bar * w[m - 1, m - 1])
                w[m, m] = (2 * m - 1) * (x_bar * w[m - 1, m - 1] + y_bar * v[m - 1, m - 1])
            # Off-diagonal terms (m < n)
            else:
                v[n, m] = (
                    (2 * n - 1) * z_bar * v[n - 1, m] - (n + m - 1) * rho_sq * v[n - 2, m]
                ) / (n - m)
                if m != 0:
                    w[n, m] = (
                        (2 * n - 1) * z_bar * w[n - 1, m] - (n + m - 1) * rho_sq * w[n - 2, m]
                    ) / (n - m)

    return v, w


def nonSphericalAcceleration(
    ecef_pos: ndarray,
    cb_mu: float,
    cb_radius: float,
    c: ndarray,
    s: ndarray,
    max_degree: int,
    max_order: int,
) -> ndarray:
    r"""Compute the non-spherical geopotential acceleration.

    Note:
        The gravity model order must be less than or equal to the gravity model degree.
        This function only considers J2 and above. It does not include Keplerian Force Accelerations.

    References:
        :cite:t:`montenbruck_2012_orbits`, Eqn 3.32 - 3.33

    Args:
        ecef_pos (``ndarray``): ITRF/ECEF for which to calculate the acceleration terms (km).
        cb_mu (``float``): central body's gravitational parameter, (km^3/sec^2).
        cb_radius (``float``): spherical radius of the central body (km).
        c (``ndarray``): cosine geopotential coefficients, not normalized.
        s (``ndarray``): sine geopotential coefficients, not normalized.
        max_degree (``int``): maximum degree (:math:`n`) of the gravity model
        max_order (``int``): maximum order (:math`m`) of the gravity model

    Returns:
        ``ndarray``: vector of geopotential acceleration terms in ITRF/ECEF coordinates
    """
    # We require one degree & order higher harmonic terms due to the partial acceleration equations
    v, w = getNonSphericalHarmonics(ecef_pos, cb_radius, max_degree + 1, max_order + 1)
    acceleration = zeros((3,), dtype=float64)
    # [NOTE]: Reverse the iteration to accumulate from smaller terms first.
    for n in range(2, max_degree + 1):
        for m in range(max_order + 1):
            # Terms above diagonal aren't used/don't exist
            if m > n:
                continue

            # Z term doesn't change
            z_acc = (n - m + 1) * (-c[n, m] * v[n + 1, m] - s[n, m] * w[n + 1, m])
            # Zonal partial acceleration terms (simplified x/y/z equations)
            if m == 0:
                x_acc = -c[n, 0] * v[n + 1, 1]
                y_acc = -c[n, 0] * w[n + 1, 1]
            # Tesseral & sectoral partial accelerations terms
            elif n >= m:
                fact_term = (n - m + 1) * (n - m + 2)
                x_acc = 0.5 * (
                    -c[n, m] * v[n + 1, m + 1]
                    - s[n, m] * w[n + 1, m + 1]
                    + fact_term * (c[n, m] * v[n + 1, m - 1] + s[n, m] * w[n + 1, m - 1])
                )
                y_acc = 0.5 * (
                    -c[n, m] * w[n + 1, m + 1]
                    + s[n, m] * v[n + 1, m + 1]
                    + fact_term * (-c[n, m] * w[n + 1, m - 1] + s[n, m] * v[n + 1, m - 1])
                )

            # Scale terms and increment non-spherical acceleration
            acceleration += array((x_acc, y_acc, z_acc), dtype=float64)

    return acceleration * cb_mu / (cb_radius**2)
