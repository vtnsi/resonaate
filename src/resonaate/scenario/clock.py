"""Defines the :class:`.ScenarioClock` class to track simulation time."""

from __future__ import annotations

# Standard Library Imports
import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

# Local Imports
from ..data import getDBConnection
from ..data.epoch import Epoch
from ..physics.time.stardate import ScenarioTime, datetimeToJulianDate

# Type Checking Imports
if TYPE_CHECKING:
    # Local Imports
    from .config.time_config import TimeConfig


class ScenarioClock:
    """The ScenarioClock Class instantiates a ScenarioClock object.

    On creation, the ScenarioClock object inserts a new epoch into the database for each time step in the simulation.

    It stores the temporal information for the associated Scenario, and
    broadcasts the current time stamp to all Agents and Estimator.
    """

    def __init__(
        self,
        start_date: datetime,
        time_span: ScenarioTime | float,
        dt_step: ScenarioTime | float,
    ) -> None:
        """Construct a `ScenarioClock` object.

        The clock inserts a new epoch into the database for each time step in the simulation.

        Args:
            start_date (:class:`.datetime`): starting UTC date of the simulation.
            time_span (:class:`.ScenarioTime` | ``float``): total simulation time span, seconds.
            dt_step (:class:`.ScenarioTime` | ``float``): simulation internal time step, seconds.
        """
        if not isinstance(start_date, datetime):
            raise TypeError(
                "ScenarioClock: start date argument must be a `datetime` or `str` object.",
            )

        self.datetime_start = start_date
        self.datetime_stop = start_date + timedelta(seconds=time_span)
        self.julian_date_start = datetimeToJulianDate(start_date)
        self.julian_date_stop = datetimeToJulianDate(self.datetime_stop)
        self.initial_time = ScenarioTime(0)
        self.time_span = ScenarioTime(time_span)
        self.dt_step = ScenarioTime(dt_step)
        self.stop_time = ScenarioTime(time_span)
        self.time = ScenarioTime(0)
        self.logger = logging.getLogger("resonaate")

        epochs = []
        sim_time_iter = ScenarioTime(0)
        while sim_time_iter <= self.time_span:
            jd_iter = sim_time_iter.convertToJulianDate(self.julian_date_start)
            epochs.append(
                Epoch(
                    julian_date=jd_iter,
                    timestampISO=(start_date + timedelta(seconds=sim_time_iter)).isoformat(
                        timespec="microseconds",
                    ),
                ),
            )

            sim_time_iter += self.dt_step

        getDBConnection().insertData(*epochs)

    def ticToc(self, dt: ScenarioTime | float | None = None) -> None:
        r"""Increment the time property by one step.

        Args:
            dt (:class:`.ScenarioTime` | ``float`` | ``None``, optional): :math:`\Delta t` to step the simulation
                forward by, in seconds. Defaults to ``None``, which then uses :attr:`~.ScenarioClock.dt_step`.
        """
        if not dt:
            self.time += self.dt_step
        else:
            self.time += ScenarioTime(dt)

    @classmethod
    def fromConfig(cls, config: TimeConfig) -> ScenarioClock:
        """Factory to create a valid :class:`.ScenarioClock` object from a config dictionary.

        Args:
            config (:class:`.TimeConfig`): corresponding configuration

        Returns:
            :class:`.ScenarioClock`: properly constructed `ScenarioClock` object
        """
        time_span = (config.stop_timestamp - config.start_timestamp).total_seconds()

        return cls(config.start_timestamp, time_span, config.physics_step_sec)

    @property
    def datetime_epoch(self):
        """Returns the current epoch of the scenario, as a datetime object.

        Returns:
            datetime: current scenario epoch
        """
        return self.datetime_start + timedelta(seconds=self.time)

    @property
    def julian_date_epoch(self):
        """Returns the current epoch of the scenario, as a julian date.

        Returns:
            JulianDate: current scenario epoch
        """
        return self.time.convertToJulianDate(self.julian_date_start)
