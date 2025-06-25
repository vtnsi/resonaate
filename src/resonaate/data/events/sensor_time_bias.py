"""Defines the :class:`.SensorTimeBiasEvent` data table class."""

from __future__ import annotations

# Standard Library Imports
from typing import TYPE_CHECKING

# Third Party Imports
from sqlalchemy import Column, Float

# Local Imports
from ...physics.time.stardate import datetimeToJulianDate
from .base import Event, EventScope

# Type Checking Imports
if TYPE_CHECKING:

    # Local Imports
    from ...agents.agent_base import Agent
    from ...scenario.config.event_configs import SensorTimeBiasEventConfig


class SensorTimeBiasEvent(Event):
    """Event data object describing a sensor time bias event."""

    EVENT_TYPE: str = "sensor_time_bias"
    """``str``: Name of this type of event."""

    INTENDED_SCOPE: EventScope = EventScope.OBSERVATION_GENERATION
    """:class:`.EventScope`: Scope where :class:`.SensorTimeBiasEvent` objects should be handled."""

    __mapper_args__ = {"polymorphic_identity": EVENT_TYPE}

    applied_bias = Column(Float)
    """``float``: amount of time to bias the sensor (seconds)."""

    MUTABLE_COLUMN_NAMES = (*Event.MUTABLE_COLUMN_NAMES, "applied_bias")

    def handleEvent(self, scope_instance: Agent) -> None:
        """Queue a :class:`.ScheduledImpulse` to take place during agent propagation.

        Args:
            scope_instance (:class:`~.agent_base.Agent`): `Agent` instance that will be executing this Time Bias.
        """
        scope_instance.appendTimeBiasEvent(self)

    @classmethod
    def fromConfig(cls, config: SensorTimeBiasEventConfig) -> SensorTimeBiasEvent:
        """Construct a :class:`.SensorTimeBiasEvent` from a specified `config`.

        Args:
            config (:class:`.SensorTimeBiasEventConfig`): Configuration object to construct a
                :class:`.SensorTimeBiasEvent` from.

        Returns:
            :class:`.SensorTimeBiasEvent`: object based on specified `config`.
        """
        return cls(
            scope=config.scope,  # EventScope.OBSERVATION_GENERATION
            scope_instance_id=config.scope_instance_id,  # Sensor ID number
            start_time_jd=datetimeToJulianDate(config.start_time),  # start timestamp
            end_time_jd=datetimeToJulianDate(config.end_time),  # end timestamp
            event_type=config.event_type,  # "sensor_time_bias"
            applied_bias=config.applied_bias,  # float of actual time bias
        )
