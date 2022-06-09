"""Defines the :class:`.FilterStep` data table class."""
# Third Party Imports
from sqlalchemy import Column, Float, ForeignKey, Integer
from sqlalchemy.orm import relationship

# Local Imports
from . import Base, _DataMixin


class FilterStep(
    Base,
    _DataMixin,
):
    """Outputs valuable information from the Unscented Kalman Filter from each filter observation."""

    __tablename__ = "filterstep"
    id = Column(Integer, primary_key=True)  # noqa: A003

    ## Defines the epoch associated with the maneuver detection data
    # Many to one relation with :class:`.Epoch`
    julian_date = Column(Float, ForeignKey("epochs.julian_date"), nullable=False)
    epoch = relationship("Epoch", lazy="joined", innerjoin=True)

    # Many to one relation with :class:`.Agent`
    target_id = Column(Integer, ForeignKey("agents.unique_id"), nullable=False)
    target = relationship("Agent", foreign_keys=[target_id], lazy="joined", innerjoin=True)

    # Measurement Residuals Corresponding to Observation
    # Size is adjustable based upon sensor type (i.e. radar or optical)
    measurement_residual_azimuth = Column(Float)
    measurement_residual_elevation = Column(Float)
    measurement_residual_range = Column(Float, nullable=True)
    measurement_residual_range_rate = Column(Float, nullable=True)

    # Innovations Corresponding to Observations
    nis = Column(Float)

    MUTABLE_COLUMN_NAMES = (
        "julian_date",
        "epoch",
        "target_id",
        "measurement_residual_azimuth",
        "measurement_residual_elevation",
        "measurement_residual_range",
        "measurement_residual_range_rate",
        "nis",
    )

    @classmethod
    def recordFilterStep(cls, **kwargs):
        """Construct an :class:`._DataMixin` object using a different format of keyword arguments.

        A keyword is provided either in a 4x1 size or a 2x1 size and if 4x1, range and range-rate
        components are written.
        """
        # Parse measurement residual array into separate columns
        kwargs["measurement_residual_azimuth"] = kwargs["innovation"][0]
        kwargs["measurement_residual_elevation"] = kwargs["innovation"][1]

        # Defining kwargs values based on size of innovations array i.e. what type of sensor
        if len(kwargs["innovation"]) == 4:
            kwargs["measurement_residual_range"] = kwargs["innovation"][2]
            kwargs["measurement_residual_range_rate"] = kwargs["innovation"][3]

        del kwargs["innovation"]

        return cls(**kwargs)

    @property
    def innovation(self):
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
