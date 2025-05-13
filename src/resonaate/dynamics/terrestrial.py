"""Defines the :class:`.Terrestrial` class for agents that are stationary on the Earth."""

from __future__ import annotations

# Standard Library Imports
from datetime import timedelta

# Local Imports
from ..physics.time.stardate import julianDateToDatetime
from ..physics.transforms.methods import ecef2eci
from .dynamics_base import Dynamics, DynamicsErrorFlag


class Terrestrial(Dynamics):
    """The Terrestrial dynamics class defines the behavior of non-moving ground-based Agents."""

    def __init__(self, jd_start, x_ecef):
        """Construct a Terrestrial object.

        Args:
            jd_start (:class:`.JulianDate`): Julian date of the scenario's initial epoch
            x_ecef (``numpy.ndarray``): Earth-fixed location of the ground-based object
        """
        self.julian_date_start = jd_start
        self.datetime_start = julianDateToDatetime(jd_start)
        self.x_ecef = x_ecef

    def propagate(
        self,
        initial_time,
        final_time,
        initial_state,
        station_keeping=None,
        scheduled_events=None,
        error_flags: DynamicsErrorFlag = DynamicsErrorFlag.COLLISION,
    ):
        """Propagate the state from the initial time to the final time.

        Args:
            initial_time (:class:`.ScenarioTime`): time value when the integration will begin (seconds)
            final_time (:class:`.ScenarioTime`): time value when the integration will stop (seconds)
            initial_state (``numpy.ndarray``): (6, ) state vector for the integration step, (km; km/sec)
            station_keeping (None): Not used.
            scheduled_events (None): Not used.
            error_flags (:class:`.DynamicsErrorFlag`): flags marking which errors will halt propagation (Not used).

        Returns:
            ``numpy.ndarray``: 6x1 ECI state vector (km; km/sec)
        """
        if final_time < initial_time:
            raise ValueError(
                "Terrestrial: Invalid input for final_time. final_time must be greater than initial_time.",
            )

        final_datetime = self.datetime_start + timedelta(seconds=final_time)
        return ecef2eci(self.x_ecef, final_datetime)
