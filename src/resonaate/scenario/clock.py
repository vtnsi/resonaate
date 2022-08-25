"""Defines the :class:`.ScenarioClock` class to track simulation time."""
from __future__ import annotations

# Standard Library Imports
import logging
from typing import TYPE_CHECKING

# Local Imports
from ..data.epoch import Epoch
from ..data.resonaate_database import ResonaateDatabase
from ..physics import constants as const
from ..physics.time.stardate import (
    JulianDate,
    ScenarioTime,
    datetimeToJulianDate,
    julianDateToDatetime,
)
from ..physics.transforms.reductions import updateReductionParameters

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
        start_date: JulianDate,
        time_span: ScenarioTime | float,
        dt_step: ScenarioTime | float,
    ) -> None:
        """Construct a `ScenarioClock` object.

        The clock inserts a new epoch into the database for each time step in the simulation.

        Args:
            start_date (:class:`.JulianDate`): starting Julian date of the simulation.
            time_span (:class:`.ScenarioTime` | ``float``): total simulation time span, seconds.
            dt_step (:class:`.ScenarioTime` | ``float``): simulation internal time step, seconds.
        """
        if not isinstance(start_date, JulianDate):
            raise TypeError("ScenarioClock: start date argument must be a `JulianDate` object.")

        self.julian_date_start = start_date
        self.julian_date_stop = JulianDate(start_date + time_span * const.SEC2DAYS)
        self.julian_date_epoch = start_date
        self.initial_time = ScenarioTime(0)
        self.time_span = ScenarioTime(time_span)
        self.dt_step = ScenarioTime(dt_step)
        self.stop_time = ScenarioTime(time_span)
        self.time = ScenarioTime(0)
        self.logger = logging.getLogger("resonaate")

        # EOP params & third body positions updated
        updateReductionParameters(start_date)

        epochs = []
        sim_time_iter = ScenarioTime(0)
        while sim_time_iter <= self.time_span:
            jd_iter = sim_time_iter.convertToJulianDate(self.julian_date_start)
            epochs.append(
                Epoch(julian_date=jd_iter, timestampISO=julianDateToDatetime(jd_iter).isoformat())
            )

            sim_time_iter += self.dt_step

        database = ResonaateDatabase.getSharedInterface()
        database.insertData(*epochs)

    def ticToc(self, dt: ScenarioTime | float | None = None) -> None:  # noqa: C901
        r"""Increment the time property by one step.

        Args:
            dt (:class:`.ScenarioTime` | ``float`` | ``None``, optional): :math:`\Delta t` to step the simulation
                forward by, in seconds. Defaults to ``None``, which then uses :attr:`~.ScenarioClock.dt_step`.
        """
        if not dt:
            self.time += self.dt_step
            self.julian_date_epoch = self.time.convertToJulianDate(self.julian_date_start)
        else:
            self.time += ScenarioTime(dt)
            self.julian_date_epoch = self.time.convertToJulianDate(self.julian_date_start)

        # EOP params & third body positions updated
        # [NOTE]: This assumes that the reduction params & third body positions will always be aligned with
        #           the main simulation time step. If we implement smoothing/multi-step prediction, then we
        #           will have to revisit this implementation. This will likely just change to DB insert/queries
        updateReductionParameters(self.julian_date_epoch)

    @classmethod
    def fromConfig(cls, config: TimeConfig) -> ScenarioClock:
        """Factory to create a valid :class:`.ScenarioClock` object from a config dictionary.

        Args:
            config (:class:`.TimeConfig`): corresponding configuration

        Returns:
            :class:`.ScenarioClock`: properly constructed `ScenarioClock` object
        """
        time_span = (config.stop_timestamp - config.start_timestamp).total_seconds()

        return cls(
            datetimeToJulianDate(config.start_timestamp), time_span, config.physics_step_sec
        )
