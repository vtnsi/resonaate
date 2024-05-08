"""Describes accurate, stable, well-documented, and performant orbital element models.

Users should be able to easily distinguish between different orbit element sets.
"""

from __future__ import annotations

# Standard Library Imports
from abc import ABCMeta, abstractmethod
from typing import TYPE_CHECKING, Any

# Third Party Imports
from numpy import array, isclose, ndarray

# Local Imports
from .. import constants as const
from ..bodies import Earth
from ..maths import wrapAngle2Pi
from . import isEccentric, isInclined
from .anomaly import meanLong2EccLong, trueAnom2MeanAnom
from .conversions import coe2eci, coe2eqe, eci2coe, eci2eqe, eqe2coe, eqe2eci
from .utils import (
    getEccentricityFromEQE,
    getInclinationFromEQE,
    getMeanMotion,
    getPeriod,
    singularityCheck,
)

if TYPE_CHECKING:
    # Local Imports
    from ...scenario.config.state_config import COEStateConfig, EQEStateConfig, StateConfig


class OrbitalElements(metaclass=ABCMeta):
    """Abstract base class for storing orbital element vectors."""

    DEFINED_FIELDS = ()

    def __init__(self, init_state: ndarray, inclined: bool, eccentric: bool):
        """Create an orbital element class from an initial state.

        Args:
            init_state (``ndarray``): initial orbital element state vector.
            inclined (``bool``): whether the orbit is inclined.
            eccentric (``bool``): whether the orbit is eccentric.
        """
        self._state = array(init_state, copy=True)
        self._init_state = array(init_state, copy=True)
        self._is_inclined = inclined
        self._is_eccentric = eccentric

    def __eq__(self, other: Any) -> bool:
        """Test if `self` is equal to `other`.

        Args:
            other (``Any``): other :class:`.OrbitalElements` object being tested for equality.

        Returns:
            ``bool``: Indication of whether `self` is equal to `other`.
        """
        for attr_name in self.DEFINED_FIELDS:
            try:
                other_attr = getattr(other, attr_name)
            except AttributeError:
                return False

            if not isclose(getattr(self, attr_name), other_attr):
                return False
        return True

    def __repr__(self) -> str:
        """Nicely represent elements in a string."""
        out = f"{self.__class__.__name__}("
        for attr_name in self.DEFINED_FIELDS:
            out += f"{attr_name}={getattr(self, attr_name):.4f},"
        return out + ")"

    @classmethod
    @abstractmethod
    def fromConfig(cls, config: StateConfig):
        """Construct an `OrbitalElements` object from a configuration dictionary.

        Args:
            config (:class:`.StateConfig`): config object that define a valid orbit.

        Returns:
            :class:`.OrbitalElements`: new `OrbitalElements` object constructed from the config.
        """

    @property
    def is_eccentric(self) -> bool:
        """``bool``: Returns whether the orbit is eccentric."""
        return self._is_eccentric

    @property
    def is_circular(self) -> bool:
        """``bool``: Returns whether the orbit is circular."""
        return not self.is_eccentric

    @property
    def is_inclined(self) -> bool:
        """``bool``: Returns whether the orbit is inclined."""
        return self._is_inclined

    @property
    def is_equatorial(self) -> bool:
        """``bool``: Returns whether the orbit is equatorial."""
        return not self.is_inclined


class ClassicalElements(OrbitalElements):
    """Define an osculating orbit using classical elements (COEs)."""

    DEFINED_FIELDS = ("sma", "ecc", "inc", "raan", "argp", "true_anomaly")

    def __init__(
        self,
        sma: float,
        ecc: float,
        inc: float,
        raan: float,
        argp: float,
        true_anom: float,
        mu: float = Earth.mu,
    ):
        r"""Define an orbit from a set of COEs.

        This class auto-checks for common COE singularities (circular and equatorial orbits). If
        a singular orbit is included, the corresponding undefined elements are set to zero:

        - Right ascension, :math:`\Omega`, is undefined for equatorial orbits.
        - Argument of perigee, :math:`\omega`, is undefined for circular orbits.

        Additionally, the anomaly variable, :math:`f`, can change depending on the type of orbit:

        - True anomaly, :math:`\nu`, for eccentric orbits
        - Argument of latitude, :math:`u=\omega + \nu`, for inclined, circular orbits
        - True longitude, :math:`\lambda_{true}\approx\Omega + \omega + \nu`, for equatorial, circular orbits

        Finally, for eccentric, equatorial orbits, argument of perigee, :math:`\omega`, is replaced with true
        longitude of periapsis, :math:`\tilde{\omega}_{true}\approx\Omega + \omega`

        Args:
            sma (``float``): semi-major axis, :math:`a` (km).
            ecc (``float``): eccentricity, :math:`e\in[0,1)`.
            inc (``float``): inclination angle, :math:`i\in[0,\pi]`, in radians.
            raan (``float``): right ascension of the ascending node, :math:`\Omega\in[0,2\pi)`, in radians.
            argp (``float``): argument of perigee, :math:`\omega\in[0,2\pi)`, the orbit (radians).
            true_anom (``float``): true anomaly (location) angle, :math:`f\in[0,2\pi)`, in radians.
            mu (``float``, optional): gravitational parameter of central body (km^3/sec^2). Defaults to
                :attr:`.Earth.mu`.

        References:
            :cite:t:`vallado_2013_astro`, Sections 2-4 - 2-6
        """
        super().__init__(
            array([sma, ecc, inc, raan, argp, true_anom]),
            isInclined(inc),
            isEccentric(ecc),
        )

        # Update raan, argp, anomaly for singular orbits
        raan, argp, true_anom = singularityCheck(ecc, inc, raan, argp, true_anom)

        # Save instance attributes
        self.sma = sma
        self.ecc = ecc
        self.inc = inc
        self.raan = raan
        self.argp = argp
        self.true_anomaly = true_anom

        # Common properties to define on construction
        self.period = getPeriod(sma, mu=mu)
        self.mean_motion = getMeanMotion(sma, mu=mu)
        self.mean_anomaly = trueAnom2MeanAnom(true_anom, ecc)

    @classmethod
    def fromECI(cls, eci_state: ndarray, mu: float = Earth.mu):
        r"""Define a set of COEs from a ECI (J2000) position and velocity vector.

        See Also:
            :func:`.eci2coe`

        Args:
            eci_state (``ndarray``): 6x1 ECI state vector (km; km/sec).
            mu (``float``, optional): gravitational parameter of central body (km^3/sec^2). Defaults to
                :attr:`.Earth.mu`.

        Returns:
            :class:`.ClassicalElements`: constructed COE object.
        """
        return cls(*eci2coe(eci_state, mu=mu))

    @classmethod
    def fromEQE(
        cls,
        sma: float,
        h: float,
        k: float,
        p: float,
        q: float,
        mean_long: float,
        retro: bool = False,
    ):
        r"""Convert an orbit defined by a set of EQEs into corresponding COEs.

        See Also:
            :func:`.eqe2coe`

        Args:
            sma (``float``): semi-major axis, :math:`a`, (km).
            h (``float``): EQE eccentricity term, :math:`h=e\sin(\omega + \Omega)`.
            k (``float``): EQE eccentricity term, :math:`k=e\cos(\omega + \Omega)`.
            p (``float``): inclination term, :math:`p=\chi=\tan(\frac{i}{2})\sin(\Omega)`.
            q (``float``): inclination term, :math:`q=\psi=\tan(\frac{i}{2})\cos(\Omega)`.
            mean_long (``float``): mean longitude (location) angle, :math:`\lambda_M\in[0,2\pi)`, in radians.
            retro (``bool``, optional): whether to use the retrograde conversion equations.

        Returns:
            :class:`.ClassicalElements`: constructed COE object.
        """
        return cls(*eqe2coe(sma, h, k, p, q, mean_long, retro=retro))

    def toECI(self, mu: float = Earth.mu) -> ndarray:
        r"""Convert a set of COEs to an ECI (J2000) position and velocity vector.

        See Also:
            :func:`.coe2eqe`

        Args:
            mu (``float``, optional): gravitational parameter of central body (km^3/sec^2). Defaults to
                :attr:`.Earth.mu`.

        Returns:
            ``ndarray``: 6x1 ECI state vector (km; km/sec).
        """
        return coe2eci(
            self.sma,
            self.ecc,
            self.inc,
            self.raan,
            self.argp,
            self.true_anomaly,
            mu=mu,
        )

    @classmethod
    def fromConfig(cls, config: COEStateConfig):
        """Construct an `ClassicalElements` object from a configuration dictionary.

        Args:
            config (:class:`.COEStateConfig`): config object that define a valid orbit.

        Returns:
            :class:`.ClassicalElements`: new `ClassicalElements` object constructed from the config.
        """
        sma = config.semi_major_axis
        ecc = config.eccentricity
        inc = config.inclination * const.DEG2RAD

        raan, argp, anomaly = 0.0, 0.0, 0.0
        if config.eccentric and config.inclined:
            raan = config.right_ascension * const.DEG2RAD
            argp = config.argument_periapsis * const.DEG2RAD
            anomaly = config.true_anomaly * const.DEG2RAD

        elif config.eccentric and not config.inclined:
            argp = config.true_longitude_periapsis * const.DEG2RAD
            anomaly = config.true_anomaly * const.DEG2RAD

        elif not config.eccentric and config.inclined:
            raan = config.right_ascension * const.DEG2RAD
            anomaly = config.argument_latitude * const.DEG2RAD

        else:
            anomaly = config.true_longitude * const.DEG2RAD

        return cls(sma, ecc, inc, raan, argp, anomaly)


class EquinoctialElements(OrbitalElements):
    """Define an osculating orbit using equinoctial elements (EQEs)."""

    DEFINED_FIELDS = ("sma", "h", "k", "p", "q", "mean_longitude")

    def __init__(
        self,
        sma: float,
        h: float,
        k: float,
        p: float,
        q: float,
        mean_longitude: float,
        retro: bool = False,
    ):
        r"""Define an orbit from a set of EQEs.

        This class auto-checks for the EQE singularity that occurs for retrograde equatorial orbits,
        :math:`i>180^{\circ} - i_{lim}` where :math:`i_{lim}` defines the numerical difference required
        for an orbit to be considered inclined.

        Args:
            sma (``float``): semi-major axis, :math:`a`, (km).
            h (``float``): EQE eccentricity term, :math:`h=e\sin(\omega + \Omega)`.
            k (``float``): EQE eccentricity term, :math:`k=e\cos(\omega + \Omega)`.
            p (``float``): inclination term, :math:`p=\chi=\tan(\frac{i}{2})\sin(\Omega)`.
            q (``float``): inclination term, :math:`q=\psi=\tan(\frac{i}{2})\cos(\Omega)`.
            mean_longitude (``float``): mean longitude (location) angle, :math:`\lambda_M\in[0,2\pi)`, in radians.
            retro (``bool``, optional): whether to use the retrograde conversion equations.

        References:
            #. :cite:t:`vallado_2013_astro`, Section 2.4.3, Pgs 108-109
            #. :cite:t:`danielson_1995_sast`, Section 2
            #. :cite:t:`vallado_2003_aiaa_covariance`
            #. :cite:t:`hintz_2008_elements`
        """
        super().__init__(
            array([sma, h, k, p, q, mean_longitude]),
            isInclined(getInclinationFromEQE(p, q)),
            isEccentric(getEccentricityFromEQE(h, k)),
        )

        # Save elements as instance variables
        self.sma = sma
        self.h = h
        self.k = k
        self.p = p
        self.q = q
        self.mean_longitude = wrapAngle2Pi(mean_longitude)
        self._is_retro = retro
        # Common properties to define on construction
        self.period = getPeriod(sma)
        self.mean_motion = getMeanMotion(sma)
        self.eccentric_longitude = meanLong2EccLong(mean_longitude, h, k)

    @property
    def is_retro(self) -> bool:
        """``bool``: Returns whether the orbit is considered 'retrograde' for singularity purposes."""
        return self._is_retro

    @classmethod
    def fromECI(cls, eci_state: ndarray, mu: float = Earth.mu, retro: bool = False):
        r"""Define a set of EQEs from a ECI (J2000) position and velocity vector.

        See Also:
            :func:`.eci2eqe`

        Args:
            eci_state (``ndarray``): 6x1 ECI state vector (km; km/sec).
            mu (``float``, optional): gravitational parameter of central body (km^3/sec^2). Defaults to
                :attr:`.Earth.mu`.
            retro (``bool``, optional): whether to use the retrograde conversion equations.

        Returns:
            :class:`.EquinoctialElements`: constructed EQE object.
        """
        return cls(*eci2eqe(eci_state, mu=mu, retro=retro))

    @classmethod
    def fromCOE(
        cls,
        sma: float,
        ecc: float,
        inc: float,
        raan: float,
        argp: float,
        true_anom: float,
        retro: bool = False,
    ):
        r"""Convert an orbit defined by a set of COEs into corresponding EQEs.

        See Also:
            :func:`.coe2eqe`

        Args:
            sma (``float``): semi-major axis, :math:`a` (km).
            ecc (``float``): eccentricity, :math:`e\in[0,1)`.
            inc (``float``): inclination angle, :math:`i\in[0,\pi]` in radians.
            raan (``float``): right ascension of the ascending node, :math:`\Omega\in[0,2\pi)`, in radians.
            argp (``float``): argument of perigee, :math:`\omega\in[0,2\pi)`, in radians.
            true_anom (``float``): true anomaly (location) angle, :math:`f\in[0,2\pi)`, in radians.
            retro (``bool``, optional): whether to use the retrograde conversion equations.

        Returns:
            :class:`.EquinoctialElements`: constructed EQE object.
        """
        return cls(*coe2eqe(sma, ecc, inc, raan, argp, true_anom, retro=retro))

    def toECI(self, mu: float = Earth.mu) -> ndarray:
        r"""Convert a set of EQEs to an ECI (J2000) position and velocity vector.

        See Also:
            :func:`.eqe2eci`

        Args:
            mu (``float``, optional): gravitational parameter of central body (km^3/sec^2). Defaults to
                :attr:`.Earth.mu`.

        Returns:
            ``ndarray``: 6x1 ECI state vector (km; km/sec).
        """
        return eqe2eci(
            self.sma,
            self.h,
            self.k,
            self.p,
            self.q,
            self.mean_longitude,
            mu=mu,
            retro=self.is_retro,
        )

    @classmethod
    def fromConfig(cls, config: EQEStateConfig):
        """Construct an `EquinoctialElements` object from a configuration dictionary.

        Args:
            config (:class:`.EQEStateConfig`): config object that define a valid EQE orbit.

        Returns:
            :class:`.EquinoctialElements`: new `EquinoctialElements` object constructed from the config.
        """
        return cls(
            config.semi_major_axis,
            config.h,
            config.k,
            config.p,
            config.q,
            config.mean_longitude * const.DEG2RAD,
            retro=config.retrograde,
        )
