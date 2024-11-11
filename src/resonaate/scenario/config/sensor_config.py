"""Defines sensor config types for describing the sensor hosted by a sensing agent."""

from __future__ import annotations

# Standard Library Imports
from abc import ABC
from typing import TYPE_CHECKING, Annotated, Literal, Union

# Third Party Imports
from numpy import inf
from pydantic import BaseModel, Field, field_validator, model_validator

# Local Imports
from ...common.labels import FoVLabel, SensorLabel
from ...physics.sensor_utils import FrequencyBand, calculateMinRadarRange
from ...sensors.optical import OPTICAL_DETECTABLE_VISMAG
from ...sensors.sensor_base import DEFAULT_VIEWING_ANGLE

# Type Checking Imports
if TYPE_CHECKING:
    # Third Party Imports
    from typing_extensions import Self

# ruff: noqa: W605, UP007


Degree0to360 = Annotated[float, Field(..., ge=0.0, lt=360.0)]
"""Type annotation denoting a floating point number :math:`\in[0, 360)`"""

Degree0to180 = Annotated[float, Field(..., gt=0.0, lt=180)]
"""Type annotation denoting a floating point number :math:`\in[0, 180]`"""

DegreeNeg90to90 = Annotated[float, Field(..., gt=-90.0, le=90)]
"""Type annotation denoting a floating point number :math:`\in[-90, 90)`"""

NonNegFloat = Annotated[float, Field(..., ge=0.0)]
"""Type annotation denoting a non-negative floating point number."""

PosFloat = Annotated[float, Field(..., gt=0.0)]
"""Type annotation denoting a positive floating point number."""


class ConicFieldOfViewConfig(BaseModel):
    R"""Configuration for the field of view of a sensor."""

    fov_shape: Literal[FoVLabel.CONIC] = FoVLabel.CONIC  # type: ignore
    R"""``str``: Type of Field of View being used."""

    cone_angle: Degree0to180 = DEFAULT_VIEWING_ANGLE
    R"""``float``: cone angle for `conic` Field of View (degrees)."""


class RectangularFieldOfViewConfig(BaseModel):
    """Configuration for the field of view of a sensor."""

    fov_shape: Literal[FoVLabel.RECTANGULAR] = FoVLabel.RECTANGULAR  # type: ignore
    R"""``str``: Type of Field of View being used."""

    azimuth_angle: Degree0to180 = DEFAULT_VIEWING_ANGLE
    R"""``float``: horizontal angular resolution for `rectangular` Field of View (degrees)."""

    elevation_angle: Degree0to180 = DEFAULT_VIEWING_ANGLE
    R"""``float``: vertical angular resolution for `rectangular` Field of View (degrees)."""


FieldOfViewConfig = Annotated[
    Union[ConicFieldOfViewConfig, RectangularFieldOfViewConfig],
    Field(..., discriminator="fov_shape"),
]


class SensorConfigBase(BaseModel, ABC):
    R"""Configuration object for a :class:`.Sensor`."""

    azimuth_range: list[Degree0to360] = Field(..., min_length=2, max_length=2)
    R"""``list[float]``: 2-element (order matters!) azimuth range mask :math:`\in[0, 360)`, degrees."""

    elevation_range: list[DegreeNeg90to90] = Field(..., min_length=2, max_length=2)
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

    minimum_range: Union[NonNegFloat, None] = None
    R"""``float, optional``: minimum range at which this sensor can observe targets, km. Defaults to a value based on sensor type."""

    maximum_range: float = inf
    R"""``float, optional``: maximum range at which this sensor can observe targets, km. Defaults to ``np.inf`` (no maximum)."""

    field_of_view: FieldOfViewConfig = Field(default_factory=RectangularFieldOfViewConfig)
    R""":class:`.FieldOfViewConfig`, optional: FOV type size to use in calculating visibility. Defaults to a rectangular FOV with default angles."""


class OpticalConfig(SensorConfigBase):
    R"""Configuration object for a :class:`.Optical`."""

    type: Literal[SensorLabel.OPTICAL] = SensorLabel.OPTICAL  # type: ignore
    R"""``str``: type of sensor being defined."""

    detectable_vismag: float = OPTICAL_DETECTABLE_VISMAG
    R"""``float``, optional: minimum detectable visual magnitude value, used for visibility constraints, unit-less. Defaults to :data:`.OPTICAL_DETECTABLE_VISMAG`."""

    @field_validator("minimum_range")
    @classmethod
    def default_min_range(cls, v):
        """Optical minimum range defaults to 0.0 km."""
        if v is None:
            return 0.0
        # else
        return v


class RadarConfig(SensorConfigBase):
    R"""Configuration object for a :class:`.Radar`."""

    type: Literal[SensorLabel.RADAR] = SensorLabel.RADAR  # type: ignore
    R"""``str``: type of sensor being defined."""

    tx_power: PosFloat
    R"""``float``: radar transmission power, W."""

    tx_frequency: Union[PosFloat, FrequencyBand]
    R"""``float``: radar transmission center frequency, Hz."""

    min_detectable_power: float = Field(..., gt=0.0)
    R"""``float``: The smallest received power that can be detected by the radar, W."""

    @field_validator("tx_frequency")
    @classmethod
    def parse_band(cls, v) -> float:
        """If a frequency band is provided for `tx_frequency`, parse it to the appropriate floating point value."""
        if isinstance(v, FrequencyBand):
            return v.mean
        # else
        return v

    @model_validator(mode="after")
    def default_min_range(self) -> Self:
        """If minimum range was not provided, set it based on frequency."""
        if self.minimum_range is None:
            self.minimum_range = calculateMinRadarRange(self.tx_frequency)
        return self


class AdvRadarConfig(RadarConfig):
    R"""Configuration object for a :class:`.AdvRadar`."""

    type: Literal[SensorLabel.ADV_RADAR] = SensorLabel.ADV_RADAR  # type: ignore
    R"""``str``: type of sensor being defined."""


SensorConfig = Annotated[
    Union[OpticalConfig, RadarConfig, AdvRadarConfig],
    Field(..., discriminator="type"),
]
