"""Module that defines the objects stored in the 'targets' and 'sensors' configuration sections."""
from __future__ import annotations

# Standard Library Imports
from dataclasses import dataclass, field
from typing import ClassVar

# Third Party Imports
from numpy import inf
from numpy.linalg import norm

# Local Imports
from ...agents import GROUND_FACILITY_LABEL, SPACECRAFT_LABEL
from ...agents.target_agent import (
    GEO_DEFAULT_MASS,
    GEO_DEFAULT_VCS,
    LEO_DEFAULT_MASS,
    LEO_DEFAULT_VCS,
    MEO_DEFAULT_MASS,
    MEO_DEFAULT_VCS,
)
from ...dynamics.integration_events.station_keeping import VALID_STATION_KEEPING_ROUTINES
from ...physics.bodies.earth import Earth
from ...physics.orbits import GEO_ALTITUDE_LIMIT, LEO_ALTITUDE_LIMIT, MEO_ALTITUDE_LIMIT
from ...sensors import (
    ADV_RADAR_LABEL,
    CONIC_FOV_LABEL,
    DEFAULT_VIEWING_ANGLE,
    OPTICAL_LABEL,
    RADAR_LABEL,
    RECTANGULAR_FOV_LABEL,
    SOLAR_PANEL_REFLECTIVITY,
    VALID_SENSOR_FOV_LABELS,
)
from ...sensors.optical import OPTICAL_DETECTABLE_VISMAG
from .base import ConfigError, ConfigObject, ConfigValueError


@dataclass
class TargetAgentConfig(ConfigObject):
    """Configuration object for a target."""

    # Config label class variable - not used by "dataclass"
    CONFIG_LABEL: ClassVar[str] = "target"
    R"""``str``: Key where settings are stored in the configuration dictionary."""

    # Basic dataclass attributes
    sat_num: int
    R"""``int``: target satellite ID number."""

    sat_name: str
    R"""``str``: target name."""

    init_eci: list[float] | None = None
    R"""``list[float]```, optional: initial ECI state vector, km; km/sec. Defaults to ``None``."""

    init_coe: dict[str, float] | None = None
    R"""``dict[str, float]```, optional: initial COE set, see :meth:`.ClassicalElements.fromConfig` for details. Defaults to ``None``."""

    init_eqe: dict[str, float] | None = None
    R"""``dict[str, float]```, optional: initial EQE set, see :meth:`.EquinoctialElements.fromConfig` for details. Defaults to ``None``."""

    visual_cross_section: float | None = None
    R"""``float``, optional: visual cross-sectional area, m^2. Defaults to a value based on orbital regime."""

    mass: float | None = None
    R"""``float``, optional: total mass, kg. Defaults to a value based on orbital regime."""

    reflectivity: float | None = None
    R"""``float``, optional: constant reflectivity, unit-less. Defaults to a value based on orbital regime."""

    station_keeping: StationKeepingConfig | dict | None = None
    R""":class:`.StationKeepingConfig`, optional: types of station-keeping to apply during propagation. Defaults to a no station-keeping routines.

    Note:
        The global :attr:`.propagation.station_keeping` must be set to ``True`` for station-keeping
        routines to actually run.
    """

    def __post_init__(self):  # noqa: C901
        R"""Runs after the dataclass is initialized."""
        # pylint: disable=too-many-branches
        # [FIXME]: we need to make a "StateConfig" class to handle the logic better
        # [FIXME]: we need a base AgentConfig class
        states_set = (self.eci_set, self.coe_set, self.eqe_set)
        if not any(states_set):
            err = f"Target {self.sat_num}: State not specified"
            raise ConfigError(self.__class__.__name__, err)

        if sum(states_set) > 1:
            err = f"Target {self.sat_num}: Duplicate state specified"
            raise ConfigError(self.__class__.__name__, err)

        if self.eci_set:
            if len(self.init_eci) != 6:
                err = f"Target {self.sat_num}: ECI vector should have 6 elements, not {len(self.init_eci)}"
                raise ConfigError(self.__class__.__name__, err)

            altitude = norm(self.init_eci[:3]) - Earth.radius

        if self.eqe_set:
            if len(self.init_eqe) != 6:
                err = f"Target {self.sat_num}: EQE set should have 6 elements, not {len(self.init_eqe)}"
                raise ConfigError(self.__class__.__name__, err)

            altitude = self.init_eqe["sma"] - Earth.radius

        if self.coe_set:
            if len(self.init_coe) < 4:
                err = f"Target {self.sat_num}: COE set should have at least 4 elements, not {len(self.init_coe)}"
                raise ConfigError(self.__class__.__name__, err)

            altitude = self.init_coe["sma"] - Earth.radius

        if altitude <= LEO_ALTITUDE_LIMIT:
            orbital_regime = "leo"
        elif altitude <= MEO_ALTITUDE_LIMIT:
            orbital_regime = "meo"
        elif altitude <= GEO_ALTITUDE_LIMIT:
            orbital_regime = "geo"
        else:
            err = "RSO altitude above GEO, unable to set a default mass value"
            raise ConfigError(self.__class__.__name__, err)

        # Set mass
        if self.mass is None:
            mass_dict = {
                "leo": LEO_DEFAULT_MASS,
                "meo": MEO_DEFAULT_MASS,
                "geo": GEO_DEFAULT_MASS,
            }
            self.mass = mass_dict[orbital_regime]

        # Set Visual Cross Section
        if self.visual_cross_section is None:
            vcs_dict = {
                "leo": LEO_DEFAULT_VCS,
                "meo": MEO_DEFAULT_VCS,
                "geo": GEO_DEFAULT_VCS,
            }
            self.visual_cross_section = vcs_dict[orbital_regime]

        # Set Reflectivity
        if self.reflectivity is None:
            self.reflectivity = SOLAR_PANEL_REFLECTIVITY

        if isinstance(self.station_keeping, dict):
            self.station_keeping = StationKeepingConfig(**self.station_keeping)
        elif self.station_keeping is None:
            self.station_keeping = StationKeepingConfig()

    @property
    def eci_set(self):
        R"""``bool``: Boolean indication of whether this sensor has ECI settings."""
        return self.init_eci is not None

    @property
    def coe_set(self):
        R"""``bool``: Indication of whether COEs are available for this target configuration."""
        return self.init_coe is not None

    @property
    def eqe_set(self):
        R"""``bool``: Indication of whether EQEs are available for this target configuration."""
        return self.init_eqe is not None


@dataclass
class SensingAgentConfig(ConfigObject):
    R"""Configuration object for a :class:`.SensingAgent`."""
    # pylint: disable=too-many-instance-attributes

    # Config label class variable - not used by "dataclass"
    CONFIG_LABEL: ClassVar[str] = "sensor"
    R"""``str``: Key where settings are stored in the configuration dictionary."""

    # Basic dataclass attributes
    id: int  # noqa: A003
    R"""``int``: unique ID of the sensor."""

    name: str
    R"""``str``: name of the sensor."""

    host_type: str
    R"""``str``: type of host agent containing this sensor, in ``"Spacecraft" | "GroundFacility"``."""

    sensor_type: str
    R"""``str``: type of sensor object, in ``"Optical" | "Radar" | "AdvRadar"``."""

    azimuth_range: list[float]
    R"""``list[float]``: 2-element (order matters!) azimuth range mask :math:`\in [0, 2\pi]` radians."""

    elevation_range: list[float]
    R"""``list[float]``: 2-element (order independent) elevation range mask :math:`\in [-\frac{\pi}{2}, \frac{\pi}{2}]` radians."""

    covariance: list[list[float]]
    R"""``list[list[float]]``: (:math:`n_z \times n_z`) measurement noise covariance matrix.

    The covariance matrix must be symmetric and positive definite. Also, the units for the
    covariance depend on the units of the measurements that the sensor reports. If a sensor
    reports measurements as a vector,

    .. math::

        z = \begin{bmatrix} z_1 \\ z_2 \\\end{bmatrix}, \quad \begin{bmatrix} s \\ km \\ \end{bmatrix}

    Then, the structure and units of :attr:`.covariance` should be

    .. math::

        R = \begin{bmatrix} a & b \\ b & c \\\end{bmatrix}, \quad \begin{bmatrix} s^2 & km\cdot s \\ km\cdot s & (km)^2 \\ \end{bmatrix}

    where :math:`R \succ 0`.
    """

    aperture_area: float
    R"""``float``: effective aperture area of the sensor, m^2."""

    efficiency: float
    R"""``float``: sensor measurement efficiency, unit-less."""

    slew_rate: float
    R"""``float``: sensor maximum slew rate, rad/sec."""

    exemplar: list[float]
    R"""``list[float]``: 2-element sensor exemplar set of `(size, distance)`, (m^2, km)."""

    lat: float | None = None
    R"""``float``, optional: sensor geodetic latitude, :math:`\in [-\frac{\pi}{2}, \frac{\pi}{2}]` radians. Defaults to ``None``"""

    lon: float | None = None
    R"""``float``, optional: sensor longitude, :math:`\in [-\pi, \pi]` radians. Defaults to ``None``"""

    alt: float | None = None
    R"""``float``, optional: sensor height above ellipsoid, km. Defaults to ``None``"""

    init_eci: list[float] | None = None
    R"""``list[float]```, optional: initial ECI state vector, km; km/sec. Defaults to ``None``."""

    init_coe: dict[str, float] | None = None
    R"""``dict[str, float]```, optional: initial COE set, see :meth:`.ClassicalElements.fromConfig` for details. Defaults to ``None``."""

    init_eqe: dict[str, float] | None = None
    R"""``dict[str, float]```, optional: initial EQE set, see :meth:`.EquinoctialElements.fromConfig` for details. Defaults to ``None``."""

    background_observations: bool = False
    R"""``bool``, optional: whether this sensor uses its :attr:`.filed_of_view` to determine if other agents are visible. Defaults to ``False``"""

    detectable_vismag: float = OPTICAL_DETECTABLE_VISMAG
    R"""``float, optional``: minimum detectable visual magnitude value, used for visibility constraints, unit-less. Defaults to :data:`.OPTICAL_DETECTABLE_VISMAG`."""

    minimum_range: float = 0.0
    R"""``float, optional``: minimum range at which this sensor can observe targets, km. Defaults to ``0.0`` (no minimum)."""

    maximum_range: float = inf
    R"""``float, optional``: maximum range at which this sensor can observe targets, km. Defaults to ``np.inf`` (no maximum)."""

    visual_cross_section: float | None = None
    R"""``float``, optional: visual cross-sectional area, m^2. Defaults to a value based on orbital regime."""

    mass: float | None = None
    R"""``float``, optional: total mass, kg. Defaults to a value based on orbital regime."""

    reflectivity: float | None = None
    R"""``float``, optional: constant reflectivity, unit-less. Defaults to a value based on orbital regime."""

    tx_power: float | None = None
    R"""``float``, optional: radar transmission power, W. Defaults to ``None``, but required for ``"Radar" | "AdvRadar"``."""

    tx_frequency: float | None = None
    R"""``float``, optional: radar transmission center frequency, Hz. Defaults to ``None``, but required for ``"Radar" | "AdvRadar"``."""

    field_of_view: FieldOfViewConfig | dict | None = None
    R""":class:`.FieldOfViewConfig`, optional: FOV type size to use in calculating visibility. Defaults to a conic FOV with default cone angle."""

    station_keeping: StationKeepingConfig | dict | None = None
    R""":class:`.StationKeepingConfig`, optional: types of station-keeping to apply during propagation. Defaults to a no station-keeping routines.

    Note:
        The global :attr:`.propagation.station_keeping` must be set to ``True`` for station-keeping
        routines to actually run.
    """

    def __post_init__(self):  # noqa: C901
        R"""Runs after the dataclass is initialized."""
        # pylint: disable=too-many-branches
        # [FIXME]: we need to make a "StateConfig" class to handle the logic better
        # [FIXME]: we need a base AgentConfig class
        # [FIXME]: add a sub-config for SensorConfig
        if self.field_of_view and isinstance(self.field_of_view, dict):
            self.field_of_view = FieldOfViewConfig(**self.field_of_view)
        elif self.field_of_view is None:
            self.field_of_view = FieldOfViewConfig(CONIC_FOV_LABEL)

        if isinstance(self.station_keeping, dict):
            self.station_keeping = StationKeepingConfig(**self.station_keeping)
        elif self.station_keeping is None:
            self.station_keeping = StationKeepingConfig()

        if self.host_type not in (GROUND_FACILITY_LABEL, SPACECRAFT_LABEL):
            err = f"Sensor {self.name}: host_type must be either {GROUND_FACILITY_LABEL} or {SPACECRAFT_LABEL}"
            raise ConfigError(self.__class__.__name__, err)

        if self.sensor_type not in (
            OPTICAL_LABEL,
            RADAR_LABEL,
            ADV_RADAR_LABEL,
        ):
            err = f"Sensor {self.name}: sensor_type must be either {OPTICAL_LABEL}, {RADAR_LABEL}, or {ADV_RADAR_LABEL}"
            raise ConfigError(self.__class__.__name__, err)

        states_set = (self.lla_set, self.eci_set, self.coe_set, self.eqe_set)
        if not any(states_set):
            err = f"Sensor {self.id}: State not specified"
            raise ConfigError(self.__class__.__name__, err)

        if sum(states_set) > 1:
            err = f"Sensor {self.id}: Duplicate state specified"
            raise ConfigError(self.__class__.__name__, err)

        if self.lla_set:
            altitude = self.alt

        if self.eci_set:
            if len(self.init_eci) != 6:
                err = f"Sensor {self.id}: ECI vector should have 6 elements, not {len(self.init_eci)}"
                raise ConfigError(self.__class__.__name__, err)

            altitude = norm(self.init_eci[:3]) - Earth.radius

        if self.eqe_set:
            if len(self.init_eqe) != 6:
                err = f"Target {self.id}: EQE set should have 6 elements, not {len(self.init_eqe)}"
                raise ConfigError(self.__class__.__name__, err)

            altitude = self.init_eqe["sma"] - Earth.radius

        if self.coe_set:
            if len(self.init_coe) < 4:
                err = f"Target {self.id}: COE set should have at least 4 elements, not {len(self.init_coe)}"
                raise ConfigError(self.__class__.__name__, err)

            altitude = self.init_coe["sma"] - Earth.radius

        is_radar = self.sensor_type in (RADAR_LABEL, ADV_RADAR_LABEL)
        tx_not_set = self.tx_power is None or self.tx_frequency is None
        if is_radar and tx_not_set:
            err = f"Sensor {self.id}: Radar transmit parameters not set"
            raise ConfigError(self.__class__.__name__, err)

        if self.host_type is GROUND_FACILITY_LABEL and self.station_keeping.routines:
            err = "Ground based sensors cannot perform station keeping"
            raise ConfigError(self.__class__.__name__, err)

        if altitude <= LEO_ALTITUDE_LIMIT:
            orbital_regime = "leo"
        elif altitude <= MEO_ALTITUDE_LIMIT:
            orbital_regime = "meo"
        elif altitude <= GEO_ALTITUDE_LIMIT:
            orbital_regime = "geo"
        else:
            err = "RSO altitude above GEO, unable to set a default mass value"
            raise ConfigError(self.__class__.__name__, err)

        # Set mass
        if self.mass is None:
            mass_dict = {
                "leo": LEO_DEFAULT_MASS,
                "meo": MEO_DEFAULT_MASS,
                "geo": GEO_DEFAULT_MASS,
            }
            self.mass = mass_dict[orbital_regime]

        # Set Visual Cross Section
        if self.visual_cross_section is None:
            vcs_dict = {
                "leo": LEO_DEFAULT_VCS,
                "meo": MEO_DEFAULT_VCS,
                "geo": GEO_DEFAULT_VCS,
            }
            self.visual_cross_section = vcs_dict[orbital_regime]

        # Set Reflectivity
        if self.reflectivity is None:
            self.reflectivity = SOLAR_PANEL_REFLECTIVITY

    @property
    def lla_set(self):
        R"""``bool``: Boolean indication of whether this sensor has LLA settings."""
        return any((self.lat is not None, self.lon is not None, self.alt is not None))

    @property
    def eci_set(self):
        R"""``bool``: Boolean indication of whether this sensor has ECI settings."""
        return self.init_eci is not None

    @property
    def coe_set(self):
        R"""``bool``: Indication of whether COEs are available for this target configuration."""
        return self.init_coe is not None

    @property
    def eqe_set(self):
        R"""``bool``: Indication of whether EQEs are available for this target configuration."""
        return self.init_eqe is not None


@dataclass
class FieldOfViewConfig(ConfigObject):
    R"""Configuration for the field of view of a sensor."""

    CONFIG_LABEL: ClassVar[str] = "field_of_view"
    R"""``str``: Key where settings are stored in the configuration dictionary."""

    fov_shape: str
    R"""``str``: Type of Field of View being used."""

    cone_angle: float = DEFAULT_VIEWING_ANGLE
    R"""``float``: cone angle for `conic` Field of View (degrees)."""

    azimuth_angle: float = DEFAULT_VIEWING_ANGLE
    R"""``float``: horizontal angular resolution for `rectangular` Field of View (degrees)."""

    elevation_angle: float = DEFAULT_VIEWING_ANGLE
    R"""``float``: vertical angular resolution for `rectangular` Field of View (degrees)."""

    def __post_init__(self):
        R"""Runs after the dataclass is initialized."""
        if self.fov_shape not in VALID_SENSOR_FOV_LABELS:
            raise ConfigValueError("fov_shape", self.fov_shape, VALID_SENSOR_FOV_LABELS)

        if self.fov_shape == CONIC_FOV_LABEL:
            if self.cone_angle <= 0 or self.cone_angle >= 180:
                raise ConfigValueError("cone_angle", self.cone_angle, "between 0 and 180")

        if self.fov_shape == RECTANGULAR_FOV_LABEL:
            if self.azimuth_angle <= 0 or self.azimuth_angle >= 180:
                raise ConfigValueError("azimuth_angle", self.azimuth_angle, "between 0 and 180")

            if self.elevation_angle <= 0 or self.elevation_angle >= 180:
                raise ConfigValueError(
                    "elevation_angle", self.elevation_angle, "between 0 and 180"
                )


@dataclass
class StationKeepingConfig(ConfigObject):
    R"""Configuration for station keeping routines."""

    CONFIG_LABEL: ClassVar[str] = "station_keeping"
    R"""``str``: Key where settings are stored in the configuration dictionary."""

    routines: list[str] = field(default_factory=list)
    R"""``list``: station keeping routines to be used."""

    def __post_init__(self):
        R"""Runs after the class is initialized."""
        for routine in self.routines:
            if routine not in VALID_STATION_KEEPING_ROUTINES:
                raise ConfigValueError("routine", routine, VALID_STATION_KEEPING_ROUTINES)

    def toJSON(self) -> dict[str, list[str]]:
        R"""Convert station keeping config section to JSON-serializable format."""
        return {"routines": self.routines}
