"""Defines the :class:`.FilterStep` data table class."""

from __future__ import annotations

# Standard Library Imports
from typing import TYPE_CHECKING

# Third Party Imports
import numpy as np
from sqlalchemy import Column, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, relationship

# RESONAATE Imports
from resonaate.estimation.kalman.kalman_filter import KalmanFilter
from resonaate.estimation.particle.particle_filter import ParticleFilter

# Local Imports
from ..common.utilities import serializeArrayKwarg, stringToNdarray
from .table_base import Base, _DataMixin

if TYPE_CHECKING:
    # RESONAATE Imports
    from resonaate.estimation.sequential_filter import SequentialFilter


class FilterStep(
    Base,
    _DataMixin,
):
    """Base class to ouptut valuable information for a given Filter from each filter observation."""

    __tablename__ = "filterstep"
    id: Mapped[int] = Column(Integer, primary_key=True)
    """``int``: Contains all of the id numbers for each filter observation."""

    julian_date: Mapped[float] = Column(Float, ForeignKey("epochs.julian_date"), nullable=False)
    """``float``: Contains all the julian dates."""
    epoch = relationship("Epoch", lazy="joined", innerjoin=True)
    """Defines the epoch associated with the maneuver detection data. Many to one relation with :class:`.Epoch`"""

    target_id: Mapped[int] = Column(Integer, ForeignKey("agents.unique_id"), nullable=False)
    """``int``: Contains all the target id numbers."""
    target = relationship("AgentModel", foreign_keys=[target_id], lazy="joined", innerjoin=True)
    """Defines the associated target agent with the task data. Many to one relation with :class:`.AgentModel`"""

    measurement_residual_azimuth: Mapped[float] = Column(Float)
    """``float``: Measurement residual corresponding to azimuth, measured in radians. Size is adjustable based on sensor type (i.e. radar or optical)."""
    measurement_residual_elevation: Mapped[float] = Column(Float)
    """``float``: Measurement residual corresponding to elevation, measured in radians. Size is adjustable based on sensor type (i.e. radar or optical)."""
    measurement_residual_range: Mapped[float] = Column(Float, nullable=True)
    """``float``: Measurement residual corresponding to range (i.e. distance beween the spacecraft and observer), measured in km.
    Size is adjustable based on sensor type (i.e. radar or optical)."""
    measurement_residual_range_rate: Mapped[float] = Column(Float, nullable=True)
    """``float``: Measurement residual corresponding to change in range per unit time (i.e. speed the spacecraft is moving towards or away from observer), measured in km/sec.
    Size is adjustable based on sensor type (i.e. radar or optical)."""

    MUTABLE_COLUMN_NAMES = (
        "julian_date",
        "epoch",
        "target_id",
        "measurement_residual_azimuth",
        "measurement_residual_elevation",
        "measurement_residual_range",
        "measurement_residual_range_rate",
    )

    @classmethod
    def recordFilterStep(cls, **kwargs):
        """Construct an :class:`._DataMixin` object using a different format of keyword arguments.

        A keyword is provided either in a 4x1 size or a 2x1 size and if 4x1, range and range-rate
        components are written.

        Any kwargs of type :class:`np.ndarray` should be passed in as their original array type.
        This method handles the json serialization and stores them in the database as a string.
        """
        if "filter" in kwargs:
            del kwargs["filter"]
        return cls(**kwargs)


class SequentialFilterStep(FilterStep):
    """Outputs valuable information from the Unscented Kalman Filter from each filter observation."""

    __tablename__ = "sequential_filter_step"

    id = Column(None, ForeignKey("filterstep.id"), primary_key=True)
    """``int``: Contains all of the id numbers for each filter observation."""

    _q_matrix: Mapped[str] = Column(String)
    """``str``: Serialized json containing the q-matrix."""

    _sigma_x_res: Mapped[str] = Column(String)
    """``str``: Serialized json containing the sigma x residual array."""  # TODO: Figure out a better description of what this is.
    _sigma_y_res: Mapped[str] = Column(String)
    """``str``: Serialized json containing the sigma y residual array."""  # TODO: Figure out a better description of what this is.

    _cross_cvr: Mapped[str] = Column(String)
    """``str``: Serialized json containing the cross covariance array."""
    _innov_cvr: Mapped[str] = Column(String)
    """``str``: Serialized json containing the innovation covariance array."""

    _kalman_gain: Mapped[str] = Column(String)
    """``str``: Serialized json containing the Kalman Gain."""

    nis = Column(Float)
    """``float``: Innovations Corresponding to Observations."""

    MUTABLE_COLUMN_NAMES = (
        *FilterStep.MUTABLE_COLUMN_NAMES,
        "nis",
        "_q_matrix",
        "_sigma_x_res",
        "_sigma_y_res",
        "_cross_cvr",
        "_innov_cvr",
        "_kalman_gain",
    )

    @classmethod
    def recordFilterStep(cls, **kwargs):
        """Construct an :class:`._DataMixin` object using a different format of keyword arguments.

        A keyword is provided either in a 4x1 size or a 2x1 size and if 4x1, range and range-rate
        components are written.

        Any kwargs of type :class:`np.ndarray` should be passed in as their original array type.
        This method handles the json serialization and stores them in the database as a string.
        """
        nominal_filter: SequentialFilter = kwargs.pop("filter", None)
        if nominal_filter is None:
            innovation = kwargs.pop("innovation", None)
            if innovation is None:
                raise ValueError(
                    "You must either pass a filter or an innovation to the SequentialFilterStep recorder",
                )

            # Parse measurement residual array into separate columns
            kwargs["measurement_residual_azimuth"] = innovation[0]
            kwargs["measurement_residual_elevation"] = innovation[1]
            # Defining kwargs values based on size of innovations array i.e. what type of sensor
            # TODO: Find a better solution that *actually* uses the sensor type
            if len(innovation) > 2:
                kwargs["measurement_residual_range"] = innovation[2]
                kwargs["measurement_residual_range_rate"] = innovation[3]
        else:
            # Parse measurement residual array into separate columns
            kwargs["measurement_residual_azimuth"] = nominal_filter.innovation[0]
            kwargs["measurement_residual_elevation"] = nominal_filter.innovation[1]
            # Defining kwargs values based on size of innovations array i.e. what type of sensor
            # TODO: Find a better solution that *actually* uses the sensor type
            if len(nominal_filter.innovation) == 4:
                kwargs["measurement_residual_range"] = nominal_filter.innovation[2]
                kwargs["measurement_residual_range_rate"] = nominal_filter.innovation[3]

            kwargs["nis"] = nominal_filter.nis.item()

            # Handle serializing the various array elements into strings
            # For any ndarray typed kwargs, serialize them into a json string.
            kwargs |= {
                "q_matrix": nominal_filter.q_matrix,
                "cross_cvr": nominal_filter.cross_cvr,
                "innov_cvr": nominal_filter.innov_cvr,
                "kalman_gain": nominal_filter.kalman_gain,
            }
        kwargs = serializeArrayKwarg("q_matrix", kwargs)
        kwargs = serializeArrayKwarg("sigma_x_res", kwargs)
        kwargs = serializeArrayKwarg("sigma_y_res", kwargs)
        kwargs = serializeArrayKwarg("cross_cvr", kwargs)
        kwargs = serializeArrayKwarg("innov_cvr", kwargs)
        kwargs = serializeArrayKwarg("kalman_gain", kwargs)

        return cls(**kwargs)

    @property
    def innovation(self) -> list:
        """``list``: List containing available components of [measurement_residual_1,...,measurement_residual_n]."""
        # Define size returned based on sensor type (radar or optical)
        if self.measurement_residual_range:
            return [
                self.measurement_residual_azimuth,
                self.measurement_residual_elevation,
                self.measurement_residual_range,
                self.measurement_residual_range_rate,
            ]

        return [self.measurement_residual_azimuth, self.measurement_residual_elevation]

    @property
    def q_matrix(self) -> np.ndarray:
        """``np.ndarray``: The Q-Matrix associated with the filter step."""
        return stringToNdarray(self._q_matrix)

    @property
    def sigma_x_res(self) -> np.ndarray:
        """``np.ndarray``: The sigma x residual array."""
        return stringToNdarray(self._sigma_x_res)

    @property
    def sigma_y_res(self) -> np.ndarray:
        """``np.ndarray``: The sigma y residual array."""
        return stringToNdarray(self._sigma_y_res)

    @property
    def cross_cvr(self) -> np.ndarray:
        """``np.ndarray``: The cross covrariance array."""
        return stringToNdarray(self._cross_cvr)

    @property
    def innov_cvr(self) -> np.ndarray:
        """``np.ndarray``: The innovation covariance array."""
        return stringToNdarray(self._innov_cvr)

    @property
    def kalman_gain(self) -> np.ndarray:
        """``np.ndarray``: The Kalman Gain array."""
        return stringToNdarray(self._kalman_gain)


class ParticleFilterStep(FilterStep):
    """Outputs valuable information from the Particle Filter from each filter observation."""

    __tablename__ = "particle_filter_step"

    id = Column(None, ForeignKey("filterstep.id"), primary_key=True)
    """``int``: Contains all of the id numbers for each filter observation."""

    _particles: Mapped[str] = Column(String)
    """``str``: Serialized json containing the filer's particles."""

    _scores: Mapped[str] = Column(String)
    """``str``: Serialized json containing the scores for each particle."""

    _particle_residuals: Mapped[str] = Column(String)
    """``str``: Serialized json containing the measurement residuals for each particle."""

    MUTABLE_COLUMN_NAMES = (
        *FilterStep.MUTABLE_COLUMN_NAMES,
        "_particles",
        "_scores",
        "_particle_residuals",
    )

    @classmethod
    def recordFilterStep(cls, **kwargs):
        """Construct an :class:`._DataMixin` object using a different format of keyword arguments.

        A keyword is provided either in a 4x1 size or a 2x1 size and if 4x1, range and range-rate
        components are written.

        Any kwargs of type :class:`np.ndarray` should be passed in as their original array type.
        This method handles the json serialization and stores them in the database as a string.
        """
        nominal_filter = kwargs.pop("filter", None)
        if nominal_filter is None:
            raise ValueError("A filter must be passed to the filter step recorder")

        # When the filter hasn't had an update cycle, the residuals are empty, so lets check for that
        residuals = (
            nominal_filter.particle_residuals.mean(axis=-1)
            if len(nominal_filter.particle_residuals.shape) > 1
            else np.zeros((4,))
        )

        # Parse measurement residual array into separate columns
        kwargs["measurement_residual_azimuth"] = residuals[0].item()
        kwargs["measurement_residual_elevation"] = residuals[1].item()

        # Defining kwargs values based on size of innovations array i.e. what type of sensor
        if residuals.shape[0] == 4:
            kwargs["measurement_residual_range"] = residuals[2].item()
            kwargs["measurement_residual_range_rate"] = residuals[3].item()

        # Handle serializing the various array elements into strings
        # For any ndarray typed kwargs, serialize them into a json string.
        kwargs |= {
            "particles": nominal_filter.population,
            "scores": nominal_filter.scores,
            "particle_residuals": nominal_filter.particle_residuals,
        }
        kwargs = serializeArrayKwarg("particles", kwargs)
        kwargs = serializeArrayKwarg("scores", kwargs)
        kwargs = serializeArrayKwarg("particle_residuals", kwargs)

        # print(kwargs)

        return cls(**kwargs)

    @property
    def innovation(self) -> list:
        """``list``: List containing available components of [measurement_residual_1,...,measurement_residual_n]."""
        # Define size returned based on sensor type (radar or optical)
        if self.measurement_residual_range:
            return [
                self.measurement_residual_azimuth,
                self.measurement_residual_elevation,
                self.measurement_residual_range,
                self.measurement_residual_range_rate,
            ]

        return [self.measurement_residual_azimuth, self.measurement_residual_elevation]

    @property
    def particles(self) -> np.ndarray:
        """``np.ndarray``: The particles comprising the filter's population."""
        return stringToNdarray(self._particles)

    @property
    def scores(self) -> np.ndarray:
        """``np.ndarray``: The scores of each particle."""
        return stringToNdarray(self._scores)

    @property
    def particle_residuals(self) -> np.ndarray:
        """``np.ndarray``: The particle residuals array."""
        return stringToNdarray(self._particle_residuals)


filter_map: dict[type[SequentialFilter] | type[ParticleFilter], type[FilterStep]] = {
    ParticleFilter: ParticleFilterStep,
    KalmanFilter: SequentialFilterStep,
}
