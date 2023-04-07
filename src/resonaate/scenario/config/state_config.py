"""Defines state config types for describing agent's location and velocity."""
from __future__ import annotations

# Standard Library Imports
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, fields
from datetime import datetime
from typing import TYPE_CHECKING, ClassVar

# Third Party Imports
from numpy import array, hstack
from scipy.linalg import norm

# Local Imports
from ...common.labels import StateLabel
from ...physics.bodies import Earth
from ...physics.constants import DEG2RAD
from ...physics.orbits.elements import ClassicalElements, EquinoctialElements
from ...physics.transforms.methods import ecef2eci, lla2ecef
from .base import ConfigError, ConfigObject, ConfigValueError

# Type Checking Imports
if TYPE_CHECKING:
    # Standard Library Imports
    from typing import Literal

    # Third Party Imports
    from numpy import ndarray
    from typing_extensions import Self


@dataclass
class StateConfig(ABC, ConfigObject):
    R"""Configuration base class defining a state."""

    VALID_LABELS: ClassVar[list[str]] = [
        StateLabel.ECI,
        StateLabel.EQE,
        StateLabel.COE,
        StateLabel.LLA,
    ]

    # Config label class variable - not used by "dataclass"
    CONFIG_LABEL: ClassVar[str] = "state"
    R"""``str``: Key where settings are stored in the configuration dictionary."""

    type: Literal["eci", "coe", "eqe", "lla"]
    R"""``str``: type of state being defined."""

    def __post_init__(self):
        R"""Runs after the dataclass is initialized."""
        if self.type not in self.VALID_LABELS:
            raise ConfigValueError("type", self.type, self.VALID_LABELS)

    @classmethod
    def fromDict(cls, state_cfg: dict) -> Self:
        R"""Construct a state config instance from a dictionary.

        Args:
            state_cfg (``dict``): config dictionary

        Raises:
            ConfigValueError: raised if an incorrect type is set
        """
        if state_cfg["type"] not in StateConfig.VALID_LABELS:
            raise ConfigValueError(
                StateConfig.CONFIG_LABEL + ".type",
                state_cfg["type"],
                StateConfig.VALID_LABELS,
            )
        return STATE_MAP[state_cfg["type"]](**state_cfg)

    @abstractmethod
    def toECI(self, utc_datetime: datetime) -> ndarray:
        R"""Convert a state config object into an ECI array.

        Args:
            utc_datetime (``datetime``): current UTC datetime epoch.

        Returns:
            ``ndarray``: 6x1 ECI state, [km; km/sec].
        """
        raise NotImplementedError


@dataclass
class ECIStateConfig(StateConfig):
    R"""Configuration defining an ECI state."""

    type: Literal["eci"]
    R"""``str``: type of state being defined."""

    position: list[float]
    R"""``list[float]``: initial 3x1 ECI position vector, km."""

    velocity: list[float]
    R"""``list[float]``: initial 3x1 ECI velocity vector, km/sec."""

    def __post_init__(self):
        R"""Runs after the dataclass is initialized."""
        super().__post_init__()
        if norm(self.position) <= Earth.radius:
            msg = f"Position magnitude must be greater than Earth's radius: {norm(self.position)}"
            raise ConfigError(self.CONFIG_LABEL + ".eci.position", msg)

    def toECI(self, utc_datetime: datetime) -> ndarray:
        R"""Convert a state config object into an ECI array.

        Args:
            utc_datetime (``datetime``): current UTC datetime epoch.

        Returns:
            ``ndarray``: 6x1 ECI state, [km; km/sec].
        """
        return hstack((self.position, self.velocity))


@dataclass
class LLAStateConfig(StateConfig):
    R"""Configuration defining an lat-lon-alt state."""

    type: Literal["lla"]
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


@dataclass
class COEStateConfig(StateConfig):
    R"""Configuration defining an COE state.

    See Also:
        :class:`.ClassicalElements` for more details on orbit definitions.
    """

    type: Literal["coe"]
    R"""``str``: type of state being defined."""

    semi_major_axis: float
    R"""``float``: semi-major axis, :math:`a`, km."""

    eccentricity: float
    R"""``float``: eccentricity, :math:`e\in[0,1)`."""

    inclination: float
    R"""``float``: inclination angle, :math:`i\in[0,180]`, degrees."""

    true_anomaly: float | None = None
    R"""``float``: true anomaly, :math:`\nu\in[0,360)`, degrees."""

    right_ascension: float | None = None
    R"""``float``: right ascension of ascending node, :math:`\Omega\in[0,360)`, degrees."""

    argument_periapsis: float | None = None
    R"""``float``: argument of periapsis, :math:`\omega\in[0,360)`, degrees."""

    true_longitude_periapsis: float | None = None
    R"""``float``: true longitude of periapsis, :math:`\tilde{\omega}_{true}\approx\Omega + \omega\in[0,360)`, degrees."""

    argument_latitude: float | None = None
    R"""``float``: argument of latitude, :math:`u=\omega + \nu\in[0,360)`, degrees."""

    true_longitude: float | None = None
    R"""``float``: true longitude, :math:`\lambda_{true}\approx\Omega + \omega + \nu\in[0,360)`, degrees."""

    inclined: bool = field(init=False)
    eccentric: bool = field(init=False)

    def __post_init__(self):
        R"""Runs after the dataclass is initialized."""
        super().__post_init__()
        if self.semi_major_axis <= Earth.radius:
            msg = f"SMA must be greater than Earth's radius: {self.semi_major_axis}"
            raise ConfigError(self.CONFIG_LABEL + ".coe.semi_major_axis", msg)

        # Checks for valid COE combos
        if (
            self.true_anomaly is not None
            and self.right_ascension is not None
            and self.argument_periapsis is not None
        ):
            self.eccentric = True
            self.inclined = True

        elif self.true_anomaly is not None and self.true_longitude_periapsis is not None:
            self.eccentric = True
            self.inclined = False

        elif self.right_ascension is not None and self.argument_latitude is not None:
            self.eccentric = False
            self.inclined = True

        elif self.true_longitude is not None:
            self.eccentric = False
            self.inclined = False

        else:
            msg = "Invalid definition of classical orbital elements, refer to ClassicalElements for details. Valid fields: \n"
            msg += f"{[f.name for f in fields(self)]}"
            raise ConfigError(self.CONFIG_LABEL + ".coe", msg)

    def toECI(self, utc_datetime: datetime) -> ndarray:
        R"""Convert a state config object into an ECI array.

        Args:
            utc_datetime (``datetime``): current UTC datetime epoch.

        Returns:
            ``ndarray``: 6x1 ECI state, [km; km/sec].
        """
        orbit = ClassicalElements.fromConfig(self)
        return orbit.toECI()


@dataclass
class EQEStateConfig(StateConfig):
    R"""Configuration defining an EQE state."""

    #  pylint: disable=invalid-name

    type: Literal["eqe"]
    R"""``str``: type of state being defined."""

    semi_major_axis: float
    R"""``float``: semi-major axis, :math:`a`, km."""

    h: float
    R"""``float``: EQE eccentricity term, :math:`h=e\sin(\omega + \Omega)`."""

    k: float
    R"""``float``: EQE eccentricity term, :math:`k=e\cos(\omega + \Omega)`."""

    p: float
    R"""``float``: inclination term, :math:`p=\chi=\tan(\frac{i}{2})\sin(\Omega)`."""

    q: float
    R"""``float``: inclination term, :math:`q=\psi=\tan(\frac{i}{2})\cos(\Omega)`."""

    mean_longitude: float
    R"""``float``: mean longitude (location) angle, :math:`\lambda_M\in[0,360)`, degrees."""

    retrograde: bool = False
    R"""``bool``: whether to use the retrograde conversion equations."""

    def __post_init__(self):
        R"""Runs after the dataclass is initialized."""
        super().__post_init__()
        if self.semi_major_axis <= Earth.radius:
            msg = f"SMA must be greater than Earth's radius: {self.semi_major_axis}"
            raise ConfigError(self.CONFIG_LABEL + ".eqe.semi_major_axis", msg)

    def toECI(self, utc_datetime: datetime) -> ndarray:
        R"""Convert a state config object into an ECI array.

        Args:
            utc_datetime (``datetime``): current UTC datetime epoch.

        Returns:
            ``ndarray``: 6x1 ECI state, [km; km/sec].
        """
        orbit = EquinoctialElements.fromConfig(self)
        return orbit.toECI()


STATE_MAP: dict[str, StateConfig] = {
    StateLabel.ECI: ECIStateConfig,
    StateLabel.LLA: LLAStateConfig,
    StateLabel.COE: COEStateConfig,
    StateLabel.EQE: EQEStateConfig,
}
