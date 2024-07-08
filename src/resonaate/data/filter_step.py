"""Defines the :class:`.FilterStep` data table class."""

from __future__ import annotations

# Standard Library Imports
import json
from json import JSONEncoder

# Third Party Imports
# Third party imports
import numpy as np
from sqlalchemy import Column, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, relationship

# Local Imports
from .table_base import Base, _DataMixin


class NumpyArrayEncoder(JSONEncoder):
    """Handles serialization of a numpy array."""

    def default(self, obj):
        """Serializes a numpy array and returns it as a json.

        Args:
            obj (np.ndarray): Numpy array you wish to serialize

        Returns:
            list, Any: Serialized json.
        """
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return JSONEncoder.default(self, obj)


def ndArrayToString(obj: np.ndarray) -> str:
    """Converts an instance of :class:`np.ndarray` to a json string.

    Args:
        obj (np.ndarray): The array you wish to convert.

    Returns:
        str: The array represented as a json string.
    """
    return json.dumps(obj, cls=NumpyArrayEncoder)


def stringToNdarray(json_string: str) -> np.ndarray:
    """Converts a serialized json string to a :class:`np.ndarray`.

    Args:
        json_string (str): The serialized json string you wish to convert.

    Returns:
        np.ndarray: Converted numpy array.
    """
    obj = json.loads(json_string)
    return np.array(obj)


class FilterStep(
    Base,
    _DataMixin,
):
    """Outputs valuable information from the Unscented Kalman Filter from each filter observation."""

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

    _q_matrix: Mapped[str] = Column(String)
    """``str``: Serialized json containing the q-matrix."""

    nis = Column(Float)
    """``float``: Innovations Corresponding to Observations."""

    MUTABLE_COLUMN_NAMES = (
        "julian_date",
        "epoch",
        "target_id",
        "measurement_residual_azimuth",
        "measurement_residual_elevation",
        "measurement_residual_range",
        "measurement_residual_range_rate",
        "nis",
        "_q_matrix",
    )

    @classmethod
    def recordFilterStep(cls, **kwargs):
        """Construct an :class:`._DataMixin` object using a different format of keyword arguments.

        A keyword is provided either in a 4x1 size or a 2x1 size and if 4x1, range and range-rate
        components are written.

        Any kwargs of type :class:`np.ndarray` should be passed in as their original array type.
        This method handles the json serialization and stores them in the database as a string.
        """
        # Parse measurement residual array into separate columns
        kwargs["measurement_residual_azimuth"] = kwargs["innovation"][0]
        kwargs["measurement_residual_elevation"] = kwargs["innovation"][1]

        # Handle serializing the various array elements into strings

        # For any ndarray typed kwargs, serialize them into a json string.

        if "q_matrix" in kwargs:
            _q_matrix: np.ndarray = kwargs["q_matrix"]
            kwargs.pop("q_matrix")
            _q_matrix_string: str = ndArrayToString(_q_matrix)
            kwargs["_q_matrix"] = _q_matrix_string

        # Defining kwargs values based on size of innovations array i.e. what type of sensor
        if len(kwargs["innovation"]) == 4:
            kwargs["measurement_residual_range"] = kwargs["innovation"][2]
            kwargs["measurement_residual_range_rate"] = kwargs["innovation"][3]

        del kwargs["innovation"]

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
