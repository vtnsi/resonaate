"""Defines state config types for describing agent's location and velocity."""

# ruff: noqa: UP007, TCH003

from __future__ import annotations

# Standard Library Imports
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Annotated, Literal, Union

# Third Party Imports
from numpy import array, hstack, ndarray
from pydantic import BaseModel, Field, PrivateAttr, model_validator
from scipy.linalg import norm
from typing_extensions import Self

# Local Imports
from ...common.labels import StateLabel
from ...physics.bodies import Earth
from ...physics.constants import DEG2RAD
from ...physics.orbits.elements import ClassicalElements, EquinoctialElements
from ...physics.transforms.methods import ecef2eci, lla2ecef


class StateConfigBase(BaseModel, ABC):
    """Abstract base class defines methods that all ``StateConfig`` children classes should implement."""

    @abstractmethod
    def toECI(self, utc_datetime: datetime) -> ndarray:
        R"""Convert a state config object into an ECI array.

        Args:
            utc_datetime (``datetime``): current UTC datetime epoch.

        Returns:
            ``ndarray``: 6x1 ECI state, [km; km/sec].
        """
        raise NotImplementedError

    @abstractmethod
    def getAltitude(self) -> float:
        R"""Return the altitude corresponding to this :class:`.StateConfig`.

        Returns:
            float: Altitude corresponding to this :class:`.StateConfig` (in km).
        """
        raise NotImplementedError


Vector3 = Annotated[list[float], Field(..., min_length=3, max_length=3)]
"""Annotated[type]: Type annotation describing a 3 element vector."""


class ECIStateConfig(StateConfigBase):
    R"""Configuration defining an ECI state."""

    type: Literal[StateLabel.ECI] = StateLabel.ECI
    R"""``str``: type of state being defined."""

    position: Vector3
    R"""``list[float]``: initial 3x1 ECI position vector, km."""

    velocity: Vector3
    R"""``list[float]``: initial 3x1 ECI velocity vector, km/sec."""

    @model_validator(mode="after")
    def pos_outside_earth(self) -> Self:
        """Validate that the specified position is outside the radius of the Earth."""
        if norm(self.position) <= Earth.radius:
            msg = f"Position magnitude must be greater than Earth's radius: {norm(self.position)}"
            raise ValueError(msg)
        return self

    def toECI(self, utc_datetime: datetime) -> ndarray:
        R"""Convert a state config object into an ECI array.

        Args:
            utc_datetime (``datetime``): current UTC datetime epoch.

        Returns:
            ``ndarray``: 6x1 ECI state, [km; km/sec].
        """
        return hstack((self.position, self.velocity))

    def getAltitude(self) -> float:
        R"""Return the altitude corresponding to this :class:`.StateConfig`.

        Note:
            Returned value is based on current position and doesn't take median altitude into
            account.

        Returns:
            float: Altitude corresponding to this :class:`.StateConfig` (in km).
        """
        return norm(self.position) - Earth.radius


class LLAStateConfig(StateConfigBase):
    R"""Configuration defining an lat-lon-alt state."""

    type: Literal[StateLabel.LLA] = StateLabel.LLA
    R"""``str``: type of state being defined."""

    latitude: float
    R"""``float``: initial geodetic latitude, degrees."""

    longitude: float
    R"""``float``: initial longitude, degrees."""

    altitude: float
    R"""``float``: initial altitude, km."""

    def toECI(self, utc_datetime: datetime) -> ndarray:
        R"""Convert a state config object into an ECI array.

        Args:
            utc_datetime (``datetime``): current UTC datetime epoch.

        Returns:
            ``ndarray``: 6x1 ECI state, [km; km/sec].
        """
        # radians, radians, km
        lla_orig = array([self.latitude * DEG2RAD, self.longitude * DEG2RAD, self.altitude])
        return ecef2eci(lla2ecef(lla_orig), utc_datetime)

    def getAltitude(self) -> float:
        R"""Return the altitude corresponding to this :class:`.StateConfig`.

        Note:
            Returned value is based on current position and doesn't take median altitude into
            account.

        Returns:
            float: Altitude corresponding to this :class:`.StateConfig` (in km).
        """
        return self.altitude


class COEStateConfig(StateConfigBase):
    R"""Configuration defining an COE state.

    See Also:
        :class:`.ClassicalElements` for more details on orbit definitions.
    """

    type: Literal[StateLabel.COE] = StateLabel.COE
    R"""``str``: type of state being defined."""

    semi_major_axis: float = Field(..., gt=Earth.radius)
    R"""``float``: semi-major axis, :math:`a`, km."""

    eccentricity: float = Field(..., ge=0.0, lt=1.0)
    R"""``float``: eccentricity, :math:`e\in[0,1)`."""

    inclination: float = Field(..., ge=0.0, le=180.0)
    R"""``float``: inclination angle, :math:`i\in[0,180]`, degrees."""

    true_anomaly: Union[float, None] = Field(default=None, ge=0.0, lt=360.0)
    R"""``float``: true anomaly, :math:`\nu\in[0,360)`, degrees."""

    right_ascension: Union[float, None] = Field(default=None, ge=0.0, lt=360.0)
    R"""``float``: right ascension of ascending node, :math:`\Omega\in[0,360)`, degrees."""

    argument_periapsis: Union[float, None] = Field(default=None, ge=0.0, lt=360.0)
    R"""``float``: argument of periapsis, :math:`\omega\in[0,360)`, degrees."""

    true_longitude_periapsis: Union[float, None] = None
    R"""``float``: true longitude of periapsis, :math:`\tilde{\omega}_{true}\approx\Omega + \omega\in[0,360)`, degrees."""

    argument_latitude: Union[float, None] = None
    R"""``float``: argument of latitude, :math:`u=\omega + \nu\in[0,360)`, degrees."""

    true_longitude: Union[float, None] = None
    R"""``float``: true longitude, :math:`\lambda_{true}\approx\Omega + \omega + \nu\in[0,360)`, degrees."""

    _inclined: bool = PrivateAttr(default=False)
    @property
    def inclined(self) -> bool:
        """bool: Indicates whether this orbit is considered inclined."""
        return self._inclined

    _eccentric: bool = PrivateAttr(default=False)
    @property
    def eccentric(self) -> bool:
        """bool: Indicates whether this orbit is considered eccentric."""
        return self._eccentric

    @model_validator(mode="after")
    def validate_elements(self) -> Self:
        R"""Runs after the model is initialized."""
        # Checks for valid COE combos
        if (
            self.true_anomaly is not None
            and self.right_ascension is not None
            and self.argument_periapsis is not None
        ):
            self._eccentric = True
            self._inclined = True

        elif self.true_anomaly is not None and self.true_longitude_periapsis is not None:
            self._eccentric = True
            self._inclined = False

        elif self.right_ascension is not None and self.argument_latitude is not None:
            self._eccentric = False
            self._inclined = True

        elif self.true_longitude is not None:
            self._eccentric = False
            self._inclined = False

        else:
            raise ValueError("Invalid definition of classical orbital elements, refer to ClassicalElements for details.")
        return self

    def toECI(self, utc_datetime: datetime) -> ndarray:
        R"""Convert a state config object into an ECI array.

        Args:
            utc_datetime (``datetime``): current UTC datetime epoch.

        Returns:
            ``ndarray``: 6x1 ECI state, [km; km/sec].
        """
        orbit = ClassicalElements.fromConfig(self)
        return orbit.toECI()

    def getAltitude(self) -> float:
        R"""Return the altitude corresponding to this :class:`.StateConfig`.

        Note:
            Returned value is based on median altitude of the orbit, so it won't be accurate for
            the entire period of the orbit.

        Returns:
            float: Altitude corresponding to this :class:`.StateConfig` (in km).
        """
        return self.semi_major_axis - Earth.radius


class EQEStateConfig(StateConfigBase):
    R"""Configuration defining an EQE state."""

    type: Literal[StateLabel.EQE] = StateLabel.EQE
    R"""``str``: type of state being defined."""

    semi_major_axis: float = Field(..., gt=Earth.radius)
    R"""``float``: semi-major axis, :math:`a`, km."""

    h: float
    R"""``float``: EQE eccentricity term, :math:`h=e\sin(\omega + \Omega)`."""

    k: float
    R"""``float``: EQE eccentricity term, :math:`k=e\cos(\omega + \Omega)`."""

    p: float
    R"""``float``: inclination term, :math:`p=\chi=\tan(\frac{i}{2})\sin(\Omega)`."""

    q: float
    R"""``float``: inclination term, :math:`q=\psi=\tan(\frac{i}{2})\cos(\Omega)`."""

    mean_longitude: float = Field(..., ge=0.0, lt=360.0)
    R"""``float``: mean longitude (location) angle, :math:`\lambda_M\in[0,360)`, degrees."""

    retrograde: bool = False
    R"""``bool``: whether to use the retrograde conversion equations."""

    def toECI(self, utc_datetime: datetime) -> ndarray:
        R"""Convert a state config object into an ECI array.

        Args:
            utc_datetime (``datetime``): current UTC datetime epoch.

        Returns:
            ``ndarray``: 6x1 ECI state, [km; km/sec].
        """
        orbit = EquinoctialElements.fromConfig(self)
        return orbit.toECI()

    def getAltitude(self) -> float:
        R"""Return the altitude corresponding to this :class:`.StateConfig`.

        Note:
            Returned value is based on median altitude of the orbit, so it won't be accurate for
            the entire period of the orbit.

        Returns:
            float: Altitude corresponding to this :class:`.StateConfig` (in km).
        """
        return self.semi_major_axis - Earth.radius


StateConfig = Annotated[
    Union[ECIStateConfig, LLAStateConfig, COEStateConfig, EQEStateConfig],
    Field(..., discriminator="type"),
]
"""Annotated[Union]: Discriminated union defining valid state configurations."""
