"""Defines sensor config types for describing the sensor hosted by a sensing agent."""

from __future__ import annotations

# Standard Library Imports
from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar

# Third Party Imports
from numpy import inf

# Local Imports
from ...common.labels import FoVLabel, SensorLabel
from ...physics.sensor_utils import calculateMinRadarRange, getFrequencyFromString
from ...sensors.optical import OPTICAL_DETECTABLE_VISMAG
from ...sensors.sensor_base import DEFAULT_VIEWING_ANGLE
from .base import ConfigObject, ConfigValueError

# Type Checking Imports
if TYPE_CHECKING:
    # Standard Library Imports
    from typing import Literal

    # Third Party Imports
    from typing_extensions import Self

# ruff: noqa: A003

VALID_SENSOR_FOV_LABELS: tuple[str] = (
    FoVLabel.CONIC,
    FoVLabel.RECTANGULAR,
)
"""``tuple``: Contains valid sensor Field of View configurations."""


@dataclass
class SensorConfig(ConfigObject):
    R"""Configuration object for a :class:`.Sensor`."""

    # Config label class variable - not used by "dataclass"
    CONFIG_LABEL: ClassVar[str] = "sensor"
    R"""``str``: Key where settings are stored in the configuration dictionary."""

    type: Literal["optical", "radar", "adv_radar"]
    R"""``str``: type of sensor being defined."""

    azimuth_range: list[float]
    R"""``list[float]``: 2-element (order matters!) azimuth range mask :math:`\in[0, 360)`, degrees."""

    elevation_range: list[float]
    R"""``list[float]``: 2-element (order independent) elevation range mask :math:`\in[-90,90)`, degrees."""

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

    aperture_diameter: float
    R"""``float``: effective aperture diameter of the sensor, :math:`\textrm{m}`."""

    efficiency: float
    R"""``float``: sensor measurement efficiency, unit-less."""

    slew_rate: float
    R"""``float``: sensor maximum slew rate, degree/sec."""

    background_observations: bool = False
    R"""``bool``, optional: whether this sensor uses its :attr:`.field_of_view` to determine if other agents are visible. Defaults to ``False``"""

    minimum_range: float | None = None
    R"""``float, optional``: minimum range at which this sensor can observe targets, km. Defaults to a value based on sensor type."""

    maximum_range: float = inf
    R"""``float, optional``: maximum range at which this sensor can observe targets, km. Defaults to ``np.inf`` (no maximum)."""

    field_of_view: FieldOfViewConfig | dict | None = None
    R""":class:`.FieldOfViewConfig`, optional: FOV type size to use in calculating visibility. Defaults to a conic FOV with default cone angle."""

    VALID_LABELS: ClassVar[list[str]] = [
        SensorLabel.OPTICAL,
        SensorLabel.RADAR,
        SensorLabel.ADV_RADAR,
    ]

    def __post_init__(self):
        R"""Runs after the dataclass is initialized."""
        if self.type not in self.VALID_LABELS:
            raise ConfigValueError("type", self.type, self.VALID_LABELS)

        if self.field_of_view and isinstance(self.field_of_view, dict):
            self.field_of_view = FieldOfViewConfig(**self.field_of_view)

        if self.field_of_view is None:
            self.field_of_view = FieldOfViewConfig(FoVLabel.RECTANGULAR)

    @classmethod
    def fromDict(cls, sensor_cfg: dict) -> Self:
        R"""Construct a sensor config instance from a dictionary.

        Args:
            sensor_cfg (``dict``): config dictionary

        Raises:
            ConfigValueError: raised if an incorrect type is set
        """
        if sensor_cfg["type"] not in SensorConfig.VALID_LABELS:
            raise ConfigValueError(
                SensorConfig.CONFIG_LABEL + ".type",
                sensor_cfg["type"],
                SensorConfig.VALID_LABELS,
            )
        return SENSOR_MAP[sensor_cfg["type"]](**sensor_cfg)


@dataclass
class OpticalConfig(SensorConfig):
    R"""Configuration object for a :class:`.Optical`."""

    type: Literal["optical"]
    R"""``str``: type of sensor being defined."""

    detectable_vismag: float = OPTICAL_DETECTABLE_VISMAG
    R"""``float``, optional: minimum detectable visual magnitude value, used for visibility constraints, unit-less. Defaults to :data:`.OPTICAL_DETECTABLE_VISMAG`."""

    def __post_init__(self):
        R"""Runs after the dataclass is initialized."""
        super().__post_init__()
        if self.minimum_range is None:
            self.minimum_range = 0.0


@dataclass
class RadarConfig(SensorConfig):
    R"""Configuration object for a :class:`.Radar`."""

    type: Literal["radar"]
    R"""``str``: type of sensor being defined."""

    tx_power: float | None = None
    R"""``float``: radar transmission power, W."""

    tx_frequency: float | str | None = None
    R"""``float``: radar transmission center frequency, Hz."""

    min_detectable_power: float | None = None
    R"""``float``: The smallest received power that can be detected by the radar, W."""

    def __post_init__(self):
        R"""Runs after the dataclass is initialized."""
        super().__post_init__()
        if self.tx_power is None:
            raise ConfigValueError(self.type + ": tx_power", self.tx_power, ">0 (W)")
        if self.tx_frequency is None:
            raise ConfigValueError(
                self.type + ": tx_frequency", self.tx_frequency, ">0 (Hz) or band"
            )
        if self.min_detectable_power is None:
            raise ConfigValueError(
                self.type + ": min_detectable_power", self.min_detectable_power, ">0 (W)"
            )

        if isinstance(self.tx_frequency, str):
            self.tx_frequency = getFrequencyFromString(self.tx_frequency.upper())

        if self.minimum_range is None:
            self.minimum_range = calculateMinRadarRange(self.tx_frequency)


@dataclass
class AdvRadarConfig(RadarConfig):
    R"""Configuration object for a :class:`.AdvRadar`."""

    type: Literal["adv_radar"]
    R"""``str``: type of sensor being defined."""


SENSOR_MAP: dict[str, SensorConfig] = {
    SensorLabel.OPTICAL: OpticalConfig,
    SensorLabel.RADAR: RadarConfig,
    SensorLabel.ADV_RADAR: AdvRadarConfig,
}


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

        if self.fov_shape == FoVLabel.CONIC and (self.cone_angle <= 0 or self.cone_angle >= 180):
            raise ConfigValueError("cone_angle", self.cone_angle, "between 0 and 180")

        if self.fov_shape == FoVLabel.RECTANGULAR:
            if self.azimuth_angle <= 0 or self.azimuth_angle >= 180:
                raise ConfigValueError("azimuth_angle", self.azimuth_angle, "between 0 and 180")

            if self.elevation_angle <= 0 or self.elevation_angle >= 180:
                raise ConfigValueError(
                    "elevation_angle", self.elevation_angle, "between 0 and 180"
                )
