"""Defines :class:`.JulianDate` & :class:`.ScenarioTime` classes and supporting functions.

The classes defined in this module will be used to rigidly differentiate between
the similar Julian Date and Scenario Time values. Both of these types of values
are always going to be `float` objects, and occasionally within the same order of
magnitude of each other, so they're easy targets for confusion.

Subclassing the `float` type will allow for easy type-checking in modules or
methods that depend on utilizing certain types of time values. A developer can
still easily pass in a `time` variable that can be used like a `float` , but
calling `type` on the variable will reveal what type of time it was initialized
to.

.. code-block:: python

    def methodUsingJulianDate(time):
        assert type(time) == JulianDate

        # ... do stuff ...

    def methodUsingScenarioTime(time):
        assert isinstance(time, ScenarioTime)

        # ... do stuff ...

    julian_date = JulianDate(123456.789)
    sTime = ScenarioTime(123456.789)

    methodUsingJulianDate(julian_date) # works
    methodUsingJulianDate(sTime) # throws exception

    methodUsingScenarioTime(julian_date) # throws exception
    methodUsingScenarioTime(sTime) # works

"""

from __future__ import annotations

# Standard Library Imports
from datetime import datetime, timedelta

# Third Party Imports
from numpy import floor, remainder

# [TODO] Add descriptions for both classes and their methods
# [TODO] Remove all the operator overload methods. Can be replaced more succinctly
# [TODO] Assert message cleanup


def days2mdh(year, day_of_year):
    """Convert a year and an epoch day to the Calendar format."""
    # Get the number of days in each month, check leap year.
    days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    if remainder(year - 1900, 4) == 0:
        days_in_month[1] = 29

    # Get integer day of year.
    day_of_year_int = floor(day_of_year)

    # Find month and day of month
    item = 1
    int_temp = 0
    while (day_of_year_int > int_temp + days_in_month[item - 1]) & (item < 12):
        int_temp += days_in_month[item - 1]
        item += 1

    month = item
    day = day_of_year_int - int_temp

    # Find hours, minutes, and seconds in the day
    hour_remainder = (day_of_year - day_of_year_int) * 24
    hour = floor(hour_remainder)
    minute_remainder = (hour_remainder - hour) * 60
    minute = floor(minute_remainder)
    second = (minute_remainder - minute) * 60

    return month, day, hour, minute, second


def getCalendarDate(julian_date):
    """From a Julian date return the calendar date & time in UTC."""
    # Find year, and the days of the year (0-366)
    temp_val = float(julian_date) - 2415019.5
    temp_u = temp_val / 365.25
    year = 1900 + floor(temp_u)
    leap_years = floor((year - 1901) * 0.25)
    day_of_year = temp_val - ((year - 1900) * 365 + leap_years)

    # Case check: Beginning of the year
    if day_of_year < 1.0:
        year -= 1
        leap_years = floor((year - 1901) * 0.25)
        day_of_year = temp_val - ((year - 1900) * 365 + leap_years)

    # Calculate the actual calendar date
    month, day, hour, minute, second = days2mdh(year, day_of_year)

    return int(year), int(month), int(day), hour, minute, second


class JulianDate(float):
    """Class representing a Julian date in floating point form.

    This class allows better introspection and conversion to other time formats.
    """

    def __add__(self, other_julian_date):
        """."""
        if isinstance(other_julian_date, ScenarioTime):
            raise TypeError(
                "JulianDate: Cannot perform operations between JulianDate/ScenarioTime objects, use conversion methods.",
            )
        return float(self) + float(other_julian_date)

    def __sub__(self, other_julian_date):
        """."""
        if isinstance(other_julian_date, ScenarioTime):
            raise TypeError(
                "JulianDate: Cannot perform operations between JulianDate/ScenarioTime objects, use conversion methods.",
            )
        return float(self) - float(other_julian_date)

    def __mul__(self, other_julian_date):
        """."""
        if isinstance(other_julian_date, ScenarioTime):
            raise TypeError(
                "JulianDate: Cannot perform operations between JulianDate/ScenarioTime objects, use conversion methods.",
            )
        return float(self) * float(other_julian_date)

    def __mod__(self, other_julian_date):
        """."""
        if isinstance(other_julian_date, ScenarioTime):
            raise TypeError(
                "JulianDate: Cannot perform operations between JulianDate/ScenarioTime objects, use conversion methods.",
            )
        return float(self) % float(other_julian_date)

    def __truediv__(self, other_julian_date):
        """."""
        if isinstance(other_julian_date, ScenarioTime):
            raise TypeError(
                "JulianDate: Cannot perform operations between JulianDate/ScenarioTime objects, use conversion methods.",
            )
        return float(self) / float(other_julian_date)

    def __lt__(self, other_julian_date):
        """."""
        if isinstance(other_julian_date, ScenarioTime):
            raise TypeError(
                "JulianDate: Cannot perform operations between JulianDate/ScenarioTime objects, use conversion methods.",
            )
        return float(self) < float(other_julian_date)

    def __le__(self, other_julian_date):
        """."""
        if isinstance(other_julian_date, ScenarioTime):
            raise TypeError(
                "JulianDate: Cannot perform operations between JulianDate/ScenarioTime objects, use conversion methods.",
            )
        return float(self) <= float(other_julian_date)

    def __eq__(self, other_julian_date):
        """."""
        if isinstance(other_julian_date, ScenarioTime):
            raise TypeError(
                "JulianDate: Cannot perform operations between JulianDate/ScenarioTime objects, use conversion methods.",
            )
        return float(self) == float(other_julian_date)

    def __ne__(self, other_julian_date):
        """."""
        if isinstance(other_julian_date, ScenarioTime):
            raise TypeError(
                "JulianDate: Cannot perform operations between JulianDate/ScenarioTime objects, use conversion methods.",
            )
        return float(self) != float(other_julian_date)

    def __gt__(self, other_julian_date):
        """."""
        if isinstance(other_julian_date, ScenarioTime):
            raise TypeError(
                "JulianDate: Cannot perform operations between JulianDate/ScenarioTime objects, use conversion methods.",
            )
        return float(self) > float(other_julian_date)

    def __ge__(self, other_julian_date):
        """."""
        if isinstance(other_julian_date, ScenarioTime):
            raise TypeError(
                "JulianDate: Cannot perform operations between JulianDate/ScenarioTime objects, use conversion methods.",
            )
        return float(self) >= float(other_julian_date)

    def __hash__(self):
        """Override hash to return just the float representation of the class."""
        return hash(float(self))

    def convertToScenarioTime(self, julian_date_start):
        """."""
        # Return ScenarioTime in seconds
        return ScenarioTime((self - julian_date_start) * 24 * 3600)

    @classmethod
    def getJulianDate(cls, year, month, day, hour, minute, second):
        """From a datetime in UTC [ymdhms], return the :class:`.JulianDate`.

        References:
            :cite:t:`vallado_2013_astro`, Section 3.5.1, Algorithm 14

        Args:
            year (int): Calendar year
            month (int): Month of the year
            day (int): Day of the month
            hour (int): Hours in the day (UTC)
            minute (int): Minutes in the hour (UTC)
            second (float): Seconds in the minute (UTC)

        Returns:
            :class:.`JulianDate`: corresponding datetime in Julian date format
        """
        # Make sure we have correct inputs for months and days
        if month > 12 or month < 1:
            raise ValueError("JulianDate: Month must be an integer (1-12).")
        if day > 31 or day < 1:
            raise ValueError("JulianDate: Day must be an integer (1-31).")

        # Determine the integer portion of the Julian date. Equation is easily
        # changed to determine modified Julian date (mjd) by subtracting 2400000.5
        m_day = day + 1721013.5
        julian_day = (
            367 * year
            - floor((7 * (year + floor((month + 9) / 12))) * 0.25)
            + floor(275 * month / 9)
            + m_day
        )
        # Ensure hr/min/sec are properly input
        if hour > 24.0 or hour < 0.0:
            raise ValueError("JulianDate: Hour must be a float (0-24).")
        if minute > 60.0 or minute < 0.0:
            raise ValueError("JulianDate: Minute must be a float (0-60).")
        if second > 60.0 or second < 0.0:
            raise ValueError("JulianDate: Second must be a float (0-60).")

        # Calculate decimal portion of Julian date
        julian_day_fraction = (second + minute * 60 + hour * 3600) / 86400

        # Sanity check on the fractional part
        if julian_day_fraction > 1.0:
            julian_day = julian_day + floor(julian_day_fraction)
            julian_day_fraction = julian_day_fraction - floor(julian_day_fraction)

        return cls(julian_day + julian_day_fraction)

    @property
    def calendar_date(self):
        """Helper method to retrieve calendar date from JulianDate object."""
        return getCalendarDate(self)

    def __repr__(self):
        """Return a string representation of this :class:`.JulianDate`."""
        date_time = julianDateToDatetime(self)

        return f"JulianDate({float(self)}, ISO={date_time.isoformat(timespec='microseconds')})"

    def __str__(self):
        """Return a string representation of this :class:`.JulianDate`."""
        return self.__repr__()


def datetimeToJulianDate(date_time):
    """Convert a ``datetime`` object to a :class:`.JulianDate` .

    Args:
        date_time (datetime): ``datetime`` object to be converted.

    Returns:
        JulianDate: Converted :class:`.JulianDate` object.
    """
    return JulianDate.getJulianDate(
        date_time.year,
        date_time.month,
        date_time.day,
        date_time.hour,
        date_time.minute,
        date_time.second + date_time.microsecond / 1e6,
    )


def julianDateToDatetime(julian_date):
    """Convert a :class:`.JulianDate` to a ``datetime`` object.

    Args:
        julian_date (JulianDate): :class:`.JulianDate` object to be converted.

    Returns:
        datetime: Converted ``datetime`` object.
    """
    year, month, day, hour, minute, second = julian_date.calendar_date
    date_time = datetime(int(year), int(month), int(day), int(hour), int(minute), int(second))
    # Handle floating-point error in JulianDate -> calendar date/time conversion
    # [NOTE] This implementation assumes that time steps will always be multiples of whole seconds.
    if int(second) != second and round(second) == 60:
        date_time += timedelta(seconds=1)

    return date_time


class ScenarioTime(float):
    """Class representing an epoch time in floating point seconds.

    This class allows better introspection and conversion to other time formats.
    """

    def __add__(self, other_scenario_time):
        """."""
        if isinstance(other_scenario_time, JulianDate):
            raise TypeError(
                "ScenarioTime: Cannot perform operations between JulianDate/ScenarioTime objects, use conversion methods.",
            )
        return ScenarioTime(float(self) + float(other_scenario_time))

    def __sub__(self, other_scenario_time):
        """."""
        if isinstance(other_scenario_time, JulianDate):
            raise TypeError(
                "ScenarioTime: Cannot perform operations between JulianDate/ScenarioTime objects, use conversion methods.",
            )
        return ScenarioTime(float(self) - float(other_scenario_time))

    def __mul__(self, other_scenario_time):
        """."""
        if isinstance(other_scenario_time, JulianDate):
            raise TypeError(
                "ScenarioTime: Cannot perform operations between JulianDate/ScenarioTime objects, use conversion methods.",
            )
        return ScenarioTime(float(self) * float(other_scenario_time))

    def __mod__(self, other_scenario_time):
        """."""
        if isinstance(other_scenario_time, JulianDate):
            raise TypeError(
                "ScenarioTime: Cannot perform operations between JulianDate/ScenarioTime objects, use conversion methods.",
            )
        return ScenarioTime(float(self) % float(other_scenario_time))

    def __truediv__(self, other_scenario_time):
        """."""
        if isinstance(other_scenario_time, JulianDate):
            raise TypeError(
                "ScenarioTime: Cannot perform operations between JulianDate/ScenarioTime objects, use conversion methods.",
            )
        return ScenarioTime(float(self) / float(other_scenario_time))

    def __lt__(self, other_scenario_time):
        """."""
        if isinstance(other_scenario_time, JulianDate):
            raise TypeError(
                "ScenarioTime: Cannot perform operations between JulianDate/ScenarioTime objects, use conversion methods.",
            )
        return float(self) < float(other_scenario_time)

    def __le__(self, other_scenario_time):
        """."""
        if isinstance(other_scenario_time, JulianDate):
            raise TypeError(
                "ScenarioTime: Cannot perform operations between JulianDate/ScenarioTime objects, use conversion methods.",
            )
        return float(self) <= float(other_scenario_time)

    def __eq__(self, other_scenario_time):
        """."""
        if isinstance(other_scenario_time, JulianDate):
            raise TypeError(
                "ScenarioTime: Cannot perform operations between JulianDate/ScenarioTime objects, use conversion methods.",
            )
        return float(self) == float(other_scenario_time)

    def __ne__(self, other_scenario_time):
        """."""
        if isinstance(other_scenario_time, JulianDate):
            raise TypeError(
                "ScenarioTime: Cannot perform operations between JulianDate/ScenarioTime objects, use conversion methods.",
            )
        return float(self) != float(other_scenario_time)

    def __gt__(self, other_scenario_time):
        """."""
        if isinstance(other_scenario_time, JulianDate):
            raise TypeError(
                "ScenarioTime: Cannot perform operations between JulianDate/ScenarioTime objects, use conversion methods.",
            )
        return float(self) > float(other_scenario_time)

    def __ge__(self, other_scenario_time):
        """."""
        if isinstance(other_scenario_time, JulianDate):
            raise TypeError(
                "ScenarioTime: Cannot perform operations between JulianDate/ScenarioTime objects, use conversion methods.",
            )
        return float(self) >= float(other_scenario_time)

    def __hash__(self):
        """Override hash to return just the float representation of the class."""
        return hash(float(self))

    def convertToJulianDate(self, julian_date_start):
        """."""
        # Return valid JulianDate instance for this scenario time
        return JulianDate(julian_date_start + float(self * (1 / (24 * 3600))))

    def convertToDatetime(self, datetime_start: datetime) -> datetime:
        """Return datetime instance for this scenario time."""
        return datetime_start + timedelta(seconds=float(self))

    def __repr__(self):
        """Return a string representation of a :class:`.ScenarioTime` object."""
        return f"ScenarioTime({float(self)} seconds)"

    def __str__(self):
        """Return a string representation of this :class:`.JulianDate`."""
        return self.__repr__()
