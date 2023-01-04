"""Classes for defining different measurement types."""
from __future__ import annotations

# Standard Library Imports
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

# Third Party Imports
from numpy import array, diagflat, matmul, random, real, zeros_like
from scipy.linalg import sqrtm

# Local Imports
from ..common.exceptions import ShapeError
from ..physics.maths import isPD
from ..physics.measurement_utils import IsAngle, getAzimuth, getElevation, getRange, getRangeRate
from ..physics.transforms.methods import getSlantRangeVector

# Type Checking Imports
if TYPE_CHECKING:
    # Standard Library Imports
    from collections.abc import Sequence
    from datetime import datetime

    # Third Party Imports
    from numpy import ndarray
    from typing_extensions import Self


class MeasurementType(ABC):
    r"""Base class for the of valid measurement types that sensors can provide.

    Each type corresponds to a different value that is calculate when a sensor observes a target.
    The class is meant to define the function/algorithm used to calculate the value as well as
    extra information about the measurement type.
    """

    LABEL: str = "notset"
    r"""``str``: label identifying the measurement type for use in :class:`.SensingAgentConfig` and :class:`.Observation` table.

    Note:
        This must be overridden by subclasses.
    """

    @abstractmethod
    def calculate(
        self, sen_eci_state: ndarray, tgt_eci_state: ndarray, utc_date: datetime
    ) -> float:
        r"""Calculate the measurement value given a sensor/target configuration.

        Note:
            This must be overridden by subclasses.

        Args:
            sen_eci_state (``ndarray``): 6x1 ECI vector of the sensor (km; km/sec).
            tgt_eci_state (``ndarray``): 6x1 ECI vector of the target (km; km/sec).
            utc_date (``datetime``): UTC datetime at which this measurement takes place.

        Returns:
            ``float``: calculated measurement value
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def is_angular(self) -> IsAngle:
        r""":class:`.IsAngle`: Returns whether this measurement is an angular value (and the domain).

        Note:
            This must be overridden by subclasses.
        """
        raise NotImplementedError


class Range(MeasurementType):
    r"""Defines a range measurement based on slant range."""

    LABEL: str = "range_km"
    r"""``str``: corresponding range measurement label in :class:`.SensingAgentConfig` and :class:`.Observation` table."""

    def calculate(
        self, sen_eci_state: ndarray, tgt_eci_state: ndarray, utc_date: datetime
    ) -> float:
        r"""Calculate the range of the target relative to the sensor.

        Args:
            sen_eci_state (``ndarray``): 6x1 ECI vector of the sensor (km; km/sec).
            tgt_eci_state (``ndarray``): 6x1 ECI vector of the target (km; km/sec).
            utc_date (``datetime``): UTC datetime at which this measurement takes place.

        Returns:
            ``float``: calculated range value, km
        """
        slant_range_sez = getSlantRangeVector(sen_eci_state, tgt_eci_state, utc_date)
        return getRange(slant_range_sez)

    @property
    def is_angular(self) -> IsAngle:
        r""":class:`.IsAngle`: This is not an angular measurement."""
        return IsAngle.NOT_ANGLE


class RangeRate(MeasurementType):
    r"""Defines a range rate measurement based on slant range."""

    LABEL: str = "range_rate_km_p_sec"
    r"""``str``: corresponding range rate measurement label in :class:`.SensingAgentConfig` and :class:`.Observation` table."""

    def calculate(
        self, sen_eci_state: ndarray, tgt_eci_state: ndarray, utc_date: datetime
    ) -> float:
        r"""Calculate the range rate of the target relative to the sensor.

        Args:
            sen_eci_state (``ndarray``): 6x1 ECI vector of the sensor (km; km/sec).
            tgt_eci_state (``ndarray``): 6x1 ECI vector of the target (km; km/sec).
            utc_date (``datetime``): UTC datetime at which this measurement takes place.

        Returns:
            ``float``: calculated range rate value, km/sec
        """
        slant_range_sez = getSlantRangeVector(sen_eci_state, tgt_eci_state, utc_date)
        return getRangeRate(slant_range_sez)

    @property
    def is_angular(self) -> IsAngle:
        r""":class:`.IsAngle`: This is not an angular measurement."""
        return IsAngle.NOT_ANGLE


class Azimuth(MeasurementType):
    r"""Defines an azimuth measurement based on slant range."""

    LABEL: str = "azimuth_rad"
    r"""``str``: corresponding azimuth measurement label in :class:`.SensingAgentConfig` and :class:`.Observation` table."""

    def calculate(
        self, sen_eci_state: ndarray, tgt_eci_state: ndarray, utc_date: datetime
    ) -> float:
        r"""Calculate the azimuth of the target relative to the sensor.

        Args:
            sen_eci_state (``ndarray``): 6x1 ECI vector of the sensor (km; km/sec).
            tgt_eci_state (``ndarray``): 6x1 ECI vector of the target (km; km/sec).
            utc_date (``datetime``): UTC datetime at which this measurement takes place.

        Returns:
            ``float``: calculated azimuth value, rad
        """
        slant_range_sez = getSlantRangeVector(sen_eci_state, tgt_eci_state, utc_date)
        return getAzimuth(slant_range_sez)

    @property
    def is_angular(self) -> IsAngle:
        r""":class:`.IsAngle`: This angular value is valid: :math:`\beta \in [0, 2\pi]`."""
        return IsAngle.ANGLE_0_2PI


class Elevation(MeasurementType):
    r"""Defines an elevation measurement based on slant range."""

    LABEL: str = "elevation_rad"
    r"""``str``: corresponding elevation rate measurement label in :class:`.SensingAgentConfig` and :class:`.Observation` table."""

    def calculate(
        self, sen_eci_state: ndarray, tgt_eci_state: ndarray, utc_date: datetime
    ) -> float:
        r"""Calculate the elevation of the target relative to the sensor.

        Args:
            sen_eci_state (``ndarray``): 6x1 ECI vector of the sensor (km; km/sec).
            tgt_eci_state (``ndarray``): 6x1 ECI vector of the target (km; km/sec).
            utc_date (``datetime``): UTC datetime at which this measurement takes place.

        Returns:
            ``float``: calculated elevation value, rad
        """
        slant_range_sez = getSlantRangeVector(sen_eci_state, tgt_eci_state, utc_date)
        return getElevation(slant_range_sez)

    @property
    def is_angular(self) -> IsAngle:
        r""":class:`.IsAngle`: This angular value is valid: :math:`\beta \in [0, 2\pi]`."""
        return IsAngle.ANGLE_NEG_PI_PI


MEASUREMENT_TYPE_MAP: dict[str, MeasurementType] = {
    meas_type.LABEL: meas_type for meas_type in MeasurementType.__subclasses__()
}
r"""``dict``: maps measurement string identifiers to their classes."""


class Measurement:
    r"""Base class for defining a common interface for measurement types."""

    def __init__(self, measurement_types: Sequence[MeasurementType], r_matrix: ndarray) -> None:
        r"""Create a measurement object representing the data that a sensor provides.

        Args:
            measurement_types (``Sequence``): `:class:`.MeasurementType` objects' provided by this
                measurement object.
            r_matrix (``ndarray``): measurement noise covariance matrix. The size of this matrix
                should be :math:`n_z \times n_z` where :math:`n_z` is the dimension of the
                measurement state vector.
        """
        self._labels = [meas_type.LABEL for meas_type in measurement_types]
        self._measurements = measurement_types
        self._angular_values = [meas.is_angular for meas in self._measurements]
        self._r_matrix = zeros_like(r_matrix)
        self._sqrt_noise_covar = zeros_like(r_matrix)
        self.r_matrix = r_matrix

    @classmethod
    def fromMeasurementLabels(cls, measurement_labels: Sequence[str], r_matrix: ndarray) -> Self:
        r"""Create a measurement object from a set of measurement type labels.

        Args:
            measurement_labels (``list``): `str` values corresponding to
                `:class:`.MeasurementType` objects' :attr:`~.MeasurementType.LABEL` provided by
                this measurement object.
            r_matrix (``ndarray``): measurement noise covariance matrix. The size of this matrix
                should be :math:`n_z \times n_z` where :math:`n_z` is the dimension of the
                measurement state vector.
        """
        measurements = [
            MEASUREMENT_TYPE_MAP[meas_type]()
            for meas_type in measurement_labels
            if meas_type in MEASUREMENT_TYPE_MAP
        ]
        return cls(measurements, r_matrix)

    def calculateMeasurement(
        self,
        sen_eci_state: ndarray,
        tgt_eci_state: ndarray,
        utc_date: datetime,
        noisy: bool = False,
    ) -> dict[str, float]:
        r"""Calculate the measurement state of for the given sensor/target configuration.

        Args:
            sen_eci_state (``ndarray``): 6x1 ECI vector of the sensor (km; km/sec).
            tgt_eci_state (``ndarray``): 6x1 ECI vector of the target (km; km/sec).
            utc_date (``datetime``): UTC datetime at which this measurement takes place.
            noisy (``bool``, optional): whether measurements should include sensor noise. Defaults to ``False``.

        Returns:
            ``dict``: measurements made by the sensor
        """
        meas_state = array(
            [meas.calculate(sen_eci_state, tgt_eci_state, utc_date) for meas in self._measurements]
        )
        if noisy:
            meas_state += self.noise
        return dict(zip(self.labels, meas_state))

    def calculateNoisyMeasurement(
        self,
        sen_eci_state: ndarray,
        tgt_eci_state: ndarray,
        utc_date: datetime,
    ) -> dict[str, float]:
        r"""Calculate a noisy measurements.

        Args:
            sen_eci_state (``ndarray``): 6x1 ECI vector of the sensor (km; km/sec).
            tgt_eci_state (``ndarray``): 6x1 ECI vector of the target (km; km/sec).
            utc_date (``datetime``): UTC datetime at which this measurement takes place.

        Returns:
            ``dict``: noisy measurements made by the sensor
        """
        return self.calculateMeasurement(sen_eci_state, tgt_eci_state, utc_date, noisy=True)

    @property
    def angular_values(self) -> list[IsAngle]:
        r"""Returns which measurements are angles as :class:`.IsAngle` values.

        The following values are valid:
            - :attr:`.NOT_ANGLE` is a non-angular measurement, no special treatment is needed
            - :attr:`.ANGLE_NEG_PI_PI` is an angular measurement valid in [-pi, pi]
            - :attr:`.ANGLE_0_2PI` is an angular measurement valid in [0, 2pi]

        Returns:
            ``list``: :class:`.IsAngle` enums defining which are angular measurements
        """
        return self._angular_values

    @property
    def dim(self) -> int:
        r"""``int``: Returns the dimension of the measurement vector."""
        return self._r_matrix.shape[0]

    @property
    def labels(self) -> list[str]:
        r"""``list[str]``: Returns measurement string types."""
        return self._labels

    @property
    def noise(self) -> ndarray:
        r"""``ndarray``: Returns randomly-generated measurement :math:`n_z \times 1` noise vector.

        .. math::

            v_k \simeq N(0; R)

        """
        return matmul(self._sqrt_noise_covar, random.randn(self._r_matrix.shape[0]))

    @property
    def r_matrix(self) -> ndarray:
        r"""``ndarray``: Returns the :math:`n_z \times n_z` measurement noise covariance matrix."""
        return self._r_matrix

    @r_matrix.setter
    def r_matrix(self, r_matrix: ndarray):
        r"""Ensure the measurement noise matrix is a square matrix.

        Args:
            r_matrix (``ndarray``): measurement noise matrix for a particular sensor
        """
        if r_matrix.ndim == 1:
            self._r_matrix = diagflat(r_matrix.ravel()) ** 2.0
        elif r_matrix.shape[0] == r_matrix.shape[1]:
            self._r_matrix = r_matrix
        else:
            raise ShapeError(f"Measurement: Invalid shape for r_matrix: {r_matrix.shape}")

        if self._r_matrix.shape[0] != len(self._measurements):
            raise ShapeError(
                f"Measurement: Shape for r_matrix doesn't match measurement length: {r_matrix.shape} vs. {len(self._measurements)}"
            )

        if not isPD(self._r_matrix):
            raise ValueError(f"Measurement: non-positive definite r_matrix: {r_matrix}")

        # Save the sqrt form of the R matrix to save computation time
        self._sqrt_noise_covar = real(sqrtm(self._r_matrix))
