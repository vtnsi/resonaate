# Standard Library Imports
import logging
from datetime import datetime
# Pip Package Imports
# RESONAATE Imports
from ..physics import constants as const
from ..physics.bodies.third_body import updateThirdBodyPositions, Moon, Sun
from ..physics.time.stardate import JulianDate, ScenarioTime, datetimeToJulianDate
from ..physics.transforms.reductions import updateReductionParameters


BODIES = {
    "sun": Sun,
    "moon": Moon,
}
"""dict: third body objects to update positions of on :meth:`~.ScenarioClock.ticToc`."""


class ScenarioClock:
    """The ScenarioClock Class instantiates a ScenarioClock object.

    It stores the temporal information for the associated Scenario, and
    broadcasts the current time stamp to all Agents and Estimator.
    """

    def __init__(self, start_date, time_span, dt_step):
        """Construct a `ScenarioClock` object."""
        if not isinstance(start_date, JulianDate):
            raise TypeError('ScenarioClock: startdate argument must be a `JulianDate` object.')

        self.julian_date_start = start_date
        self.julian_date_stop = start_date + time_span * const.SEC2DAYS
        self.julian_date_epoch = start_date
        self.initial_time = ScenarioTime(0)
        self.time_span = ScenarioTime(time_span)
        self.dt_step = ScenarioTime(dt_step)
        self.stop_time = ScenarioTime(time_span)
        self.time = ScenarioTime(0)
        self.logger = logging.getLogger("resonaate")

        # EOP params & third body positions updated
        updateReductionParameters(start_date)
        updateThirdBodyPositions(start_date, BODIES)

    def ticToc(self, *args):  # noqa: C901
        """Increment the time property by one step, update class variables, and execute require callbacks."""
        if not args:
            self.time += self.dt_step
            self.julian_date_epoch = self.time.convertToJulianDate(self.julian_date_start)
        else:
            self.time += ScenarioTime(args[0])
            self.julian_date_epoch = self.time.convertToJulianDate(self.julian_date_start)

        # EOP params & third body positions updated
        # [NOTE]: This assumes that the reduction params & third body positions will always be aligned with
        #           the main simulation time step. If we implement smoothing/multi-step prediction, then we
        #           will have to revisit this implementation. This will likely just change to DB insert/queries
        updateReductionParameters(self.julian_date_epoch)
        updateThirdBodyPositions(self.julian_date_epoch, BODIES)

    ## [REVIEW][implementation] Double check this implementation!
    def reset(self):
        """Reset the `ScenarioClock` object."""
        self.time = self.initial_time
        self.julian_date_epoch = self.julian_date_start
        updateReductionParameters(self.julian_date_epoch)
        updateThirdBodyPositions(self.julian_date_epoch, BODIES)

    @classmethod
    def fromConfig(cls, config):
        """Factory to create a valid :class:`.ScenarioClock` object from a config dictionary.

        Args:
            config (``dict``): corresponding configuration

        Returns:
            :class:`.ScenarioClock`: properly constructed `ScenarioClock` object
        """
        # Parse start & stop times and calc the timespan
        if isinstance(config["start_timestamp"], datetime):
            start_time = config["start_timestamp"]
            stop_time = config["stop_timestamp"]
        else:
            start_time = datetime.strptime(
                config["start_timestamp"],
                "%Y-%m-%dT%H:%M:%S.%fZ"
            )
            stop_time = datetime.strptime(
                config["stop_timestamp"],
                "%Y-%m-%dT%H:%M:%S.%fZ"
            )
        time_span = (stop_time - start_time).total_seconds()

        return cls(
            datetimeToJulianDate(start_time),
            time_span,
            config["physics_step_sec"]
        )
