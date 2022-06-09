"""Defines common orbital anomaly conversions."""
# Standard Library Imports
# Third Party Imports
from numpy import arctan2, cos, sin, sqrt
# RESONAATE Imports
from . import check_ecc, wrap_anomaly, isEccentric
from .kepler import keplerSolveCOE, keplerSolveEQE
from .utils import getEccentricityFromEQE
from ..constants import PI
from ..math import wrapAngle2Pi


@wrap_anomaly
@check_ecc
def trueAnom2MeanAnom(nu: float, ecc: float) -> float:
    r"""Convert true anomaly to mean anomaly.

    Only valid for elliptical orbits: :math:`e < 1`.

    Args:
        nu (``float``): true anomaly, :math:`\nu`, in radians.
        ecc (``float``): eccentricity, :math:`e`.

    Returns:
        ``float``: mean anomaly in radians, :math:`M\in[0, 2\pi)`.
    """
    # pylint: disable=invalid-name
    E = trueAnom2EccAnom(nu, ecc)
    return eccAnom2MeanAnom(E, ecc)


@wrap_anomaly
@check_ecc
def meanAnom2TrueAnom(M: float, ecc: float) -> float:
    r"""Convert mean anomaly to true anomaly.

    This requires solving Kepler's equation via iteration. The mean anomaly is automatically
    forced into :math:`[0, 2\pi)`. Initial guess for eccentric anomaly is selected via method described
    in Vallado. Only valid for elliptical orbits: :math:`e < 1`.

    References:
        :cite:t:`vallado_2013_astro`, Pgs 74 - 75

    Args:
        M (``float``): mean anomaly, :math:`M`, in radians.
        ecc (``float``): eccentricity, :math:`e`.

    Returns:
        ``float``: true anomaly in radians, :math:`\nu\in[0, 2\pi)`.
    """
    # pylint: disable=invalid-name
    E = meanAnom2EccAnom(M, ecc)
    return eccAnom2TrueAnom(E, ecc)


@wrap_anomaly
@check_ecc
def trueAnom2EccAnom(nu: float, ecc: float) -> float:
    r"""Convert true anomaly to eccentric anomaly.

    Only valid for elliptical orbits: :math:`e < 1`.

    References:
        :cite:t:`vallado_2013_astro`, Eqn 2-9

    Args:
        nu (``float``): true anomaly, :math:`\nu`, in radians.
        ecc (``float``): eccentricity, :math:`e`.

    Returns:
        ``float``: eccentric anomaly in radians, :math:`E\in[0, 2\pi)`.
    """
    # pylint: disable=invalid-name
    return arctan2(sin(nu) * sqrt(1 - ecc**2), ecc + cos(nu))


@wrap_anomaly
@check_ecc
def eccAnom2TrueAnom(E: float, ecc: float) -> float:
    r"""Convert eccentricity anomaly to true anomaly.

    Only valid for elliptical orbits: :math:`e < 1`.

    References:
        :cite:t:`vallado_2013_astro`, Eqn 2-10 & 2-12

    Args:
        E (``float``): eccentric anomaly, :math:`E`, in radians.
        ecc (``float``): eccentricity, :math:`e`.

    Returns:
        ``float``: true anomaly in radians, :math:`\nu\in[0, 2\pi)`.
    """
    # pylint: disable=invalid-name
    return arctan2(sin(E) * sqrt(1 - ecc**2), cos(E) - ecc)


@wrap_anomaly
@check_ecc
def eccAnom2MeanAnom(E: float, ecc: float) -> float:
    r"""Convert eccentricity anomaly to mean anomaly.

    Only valid for elliptical orbits: :math:`e < 1`.

    References:
        :cite:t:`vallado_2013_astro`, Eqn 2-10 & 2-12

    Args:
        E (``float``): eccentric anomaly, :math:`E`, in radians.
        ecc (``float``): eccentricity, :math:`e`.

    Returns:
        ``float``: mean anomaly in radians, :math:`M\in[0, 2\pi)`.
    """
    # pylint: disable=invalid-name
    return E - ecc * sin(E)


@wrap_anomaly
@check_ecc
def meanAnom2EccAnom(M: float, ecc: float) -> float:
    r"""Convert mean anomaly to eccentric anomaly.

    This requires solving Kepler's equation via iteration. The mean anomaly is automatically
    forced into :math:`[-\pi, \pi]`. Initial guess for eccentric anomaly is selected via method described
    in :cite:p:`vallado_2013_astro`. Only valid for elliptical orbits: :math:`e < 1`.

    References:
        :cite:t:`vallado_2013_astro`, Pgs 74 - 75

    Args:
        M (``float``): mean anomaly, :math:`M`, in radians.
        ecc (``float``): eccentricity, :math:`e`.

    Returns:
        ``float``: eccentric anomaly in radians, :math:`E\in[0, 2\pi)`.
    """
    # pylint: disable=invalid-name
    M = wrapAngle2Pi(M)
    if M > PI:
        E_0 = M - ecc
    else:
        E_0 = M + ecc

    return keplerSolveCOE(E_0, M, ecc)


@wrap_anomaly
def eccLong2MeanLong(F: float, h: float, k: float) -> float:
    r"""Convert eccentric longitude to mean longitude using Kepler's equation.

    This uses the equinoctial form of Kepler's equation

    .. math::

        \lambda=F + h\cos{F} - k\sin{F}

    Only valid for elliptical orbits: :math:`e < 1`.

    References:
        :cite:t:`danielson_1995_sast`, Section 2.1.4, Eqn 2

    Args:
        F (``float``): eccentric longitude, :math:`F`, in radians.
        h (``float``): EQE eccentricity term, :math:`h=e\sin(\omega + \Omega)`.
        k (``float``): EQE eccentricity term, :math:`k=e\cos(\omega + \Omega)`.

    Returns:
        ``float``: mean longitude in radians, :math:`\lambda\in[0, 2\pi)`.
    """
    # pylint: disable=invalid-name
    if not isEccentric(getEccentricityFromEQE(h, k)):
        return F

    # else
    return F + h * cos(F) - k * sin(F)


@wrap_anomaly
def meanLong2EccLong(lam: float, h: float, k: float) -> float:
    r"""Convert mean longitude to eccentric longitude using Kepler's equation.

    This requires solving Kepler's equation via iteration. The mean longitude is automatically
    forced into :math:`[0, 2\pi)`. Initial guess for eccentric longitude is set to the mean longitude as
    described in :cite:p:`danielson_1995_sast`. Only valid for elliptical orbits: :math:`e < 1`.
    This uses the equinoctial form of Kepler's equation:

    .. math::

        \lambda=F + h\cos{F} - k\sin{F}

    References:
        :cite:t:`danielson_1995_sast`, Section 2.1.4, Eqn 2

    Args:
        lam (``float``): mean longitude, :math:`\lambda=M + \omega + \Omega`, in radians.
        h (``float``): EQE eccentricity term, :math:`h=e\sin(\omega + \Omega)`.
        k (``float``): EQE eccentricity term, :math:`k=e\cos(\omega + \Omega)`.

    Returns:
        ``float``: eccentric longitude in radians, :math:`F\in[0, 2\pi)`.
    """
    # pylint: disable=invalid-name
    if not isEccentric(getEccentricityFromEQE(h, k)):
        return lam

    # else
    lam = wrapAngle2Pi(lam)
    return keplerSolveEQE(lam, h, k, lam)


@wrap_anomaly
def meanLong2TrueAnom(lam: float, ecc: float, raan: float, argp: float, retro: bool = False) -> float:
    r"""Convert mean longitude to true anomaly.

    This requires solving Kepler's equation via iteration. Only valid for elliptical orbits: :math:`e < 1`.

    References:
        :cite:t:`danielson_1995_sast`, Section 2.1.2, Eqn 1

    Args:
        lam (``float``): mean longitude, :math:`\lambda=M + \omega + \Omega`, in radians.
        ecc (``float``): eccentricity, :math:`e`.
        raan (``float``): right ascension of the ascending node, :math:`\Omega\in[0,2\pi)`, in radians.
        argp (``float``): argument of perigee, :math:`\omega\in[0,2\pi)`, in radians.
        retro (``bool``, optional): whether to use the retrograde conversion equations.

    Returns:
        ``float``: true anomaly in radians, :math:`\nu\in[0, 2\pi)`.
    """
    # pylint: disable=invalid-name
    II = 1 if not retro else -1
    return meanAnom2TrueAnom(lam - argp - II * raan, ecc)


@wrap_anomaly
def trueAnom2MeanLong(nu: float, ecc: float, raan: float, argp: float, retro: bool = False) -> float:
    r"""Convert mean longitude to true anomaly.

    This requires solving Kepler's equation via iteration. Only valid for elliptical orbits: :math:`e < 1`.

    References:
        :cite:t:`danielson_1995_sast`, Section 2.1.2, Eqn 1

    Args:
        nu (``float``): true anomaly in radians, :math:`\nu\in[0, 2\pi)`.
        ecc (``float``): eccentricity, :math:`e`.
        raan (``float``): right ascension of the ascending node, :math:`\Omega\in[0,2\pi)`, in radians.
        argp (``float``): argument of perigee, :math:`\omega\in[0,2\pi)`, in radians.
        retro (``bool``, optional): whether to use the retrograde conversion equations.

    Returns:
        ``float``: mean longitude, :math:`\lambda=M + \omega + \Omega`, in radians.
    """
    # pylint: disable=invalid-name
    II = 1 if not retro else -1
    return trueAnom2MeanAnom(nu, ecc) + argp + II * raan
