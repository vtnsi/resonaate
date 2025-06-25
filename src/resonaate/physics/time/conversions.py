"""Helper functions that convert between different forms of time."""

from __future__ import annotations

# Standard Library Imports
import datetime

# Third Party Imports
from numpy import floor, remainder

# Local Imports
from ...common.logger import resonaateLogError
from ...physics import constants as const
from ..maths import wrapAngle2Pi
from .stardate import JulianDate, julianDateToDatetime


def greenwichMeanTime(julian_date):
    """Determine the Greenwich sidereal time associated with the given julian_date.

    References:
        :cite:t:`vallado_2013_astro`, Section 3.5.2

    Args:
        julian_date (:class:`.JulianDate`): Julian date to convert to GST

    Returns:
        float: Greenwich sidereal time in radians
    """
    # Implementation
    tut1 = (float(julian_date) - 2451545.0) / 36525.0
    gst = (
        -6.2e-6 * tut1**3
        + 0.093104 * tut1**2
        + (876600 * 3600 + 8640184.812866) * tut1
        + 67310.54841
    )
    # Convert from seconds to radians
    return wrapAngle2Pi(gst * (1 / 240) * const.DEG2RAD)


def greenwichApparentTime(year, elapsed_days, eq_equinox):
    """Determine the Greenwich apparent time.

    References:
        :cite:t:`vallado_2013_astro`, Section 3.5.2

    Args:
        year (int): Current year
        elapsed_days (float): current number of elapsed days and day fraction since January 1st
        eq_equinox (float): equation of the equinoxes

    Returns:
        float: Greenwich apparent time in radians
    """
    # GMST at 0h:0m:0.0s on Jan 1st of the current (year)
    julian_date_jan1 = JulianDate.getJulianDate(year, 1, 1, 0, 0, 0)
    julian_centuries_jan1 = (julian_date_jan1 - 2451545.0) / 36525.0
    gmst_jan1 = greenwichMeanTime(julian_date_jan1)
    # Earth's rotation rate (Eq. 3-40 Vallado Ed. 4)
    earth_rotation_rate = (
        1.002737909350795 + 5.9006e-11 * julian_centuries_jan1 - 5.9e-15 * julian_centuries_jan1**2
    )
    # GMST of the exact time
    gmst = gmst_jan1 + earth_rotation_rate * elapsed_days * const.TWOPI
    # Convert to apparent GST
    return wrapAngle2Pi(gmst + eq_equinox)


def utc2TerrestrialTime(year, month, day, hour, minute, second, delta_atomic_time):
    """Convert UTC to Terrestrial Time.

    Convert UTC time, in ymdhms form, into terrestrial time, in units of
    seconds and Julian centuries. Functionally equivalent to algorithm in:

        Fundamentals of Astrodynamics & Applications, David Vallado, Fourth Edition, 2013.

        http://celestrak.com/software/vallado-sw.asp

    References:
        :cite:t:`vallado_2013_astro`, Section 3.5.5, Algorithm 16

    Note: convtime function in Vallado SOFTWARE omits fractional part:
        TTT = (jd - 2451545.0)/36525;

    Args:
        year (int): current year
        month (int): current month
        day (int): current day of month
        hour (int): hour of the day
        minute (int): minute of the hour
        second (float): seconds of the minute
        delta_atomic_time (float): atomic time correction term

    Returns:
        tuple: the terrestrial time in seconds and in Julian centuries
    """
    # Get UTC in seconds. Convert to atomic time and then terrestrial time in seconds. Eq. 3-49 Vallado Ed. 4
    utc = hour * 3600 + minute * 60 + second
    tai = utc + delta_atomic_time
    # Constant is difference between atomic time and terrestrial time
    tt_secs = tai + 32.184

    # Convert terrestrial time back to hms form
    hr_temp, min_temp, sec_temp = seconds2hms(tt_secs)
    # Get Julian day. Convert to Julian centuries since J2000 epoch, Eq. 3-42 Vallado 4th Ed.
    julian_date = JulianDate.getJulianDate(year, month, day, hr_temp, min_temp, sec_temp)
    ttt = (float(julian_date) - 2451545) / 36525

    return tt_secs, ttt


def seconds2hms(total_seconds):
    """Convert total seconds in a day to hour, minute, second format.

    References:
        :cite:t:`vallado_2013_astro`, Section 3.6.3
    """
    temp = total_seconds / 3600
    hour = floor(temp)
    minute = floor((temp - hour) * 60)
    second = (temp - hour - minute / 60) * 3600

    return hour, minute, second


def dayOfYear(year, month, day, hour, minute, second):
    """Determine the fractional day of the year.

    References:
        :cite:t:`vallado_2013_astro`, Section 3.6.4
    """
    # Regular number of days in a month
    days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

    # Check for leap years for February days
    if remainder(year, 4) == 0:
        days_in_month[1] = 29
        # Multiples of 100, 200, 300 are not included in leap years, multiples of 400 are included
        if (remainder(year, 100) == 0) and (remainder(year, 400) != 0):
            days_in_month[1] = 28

    # Sum up total days up to the current month
    count = 1
    days = 0
    while (count < month) and (count < 12):
        days += days_in_month[count - 1]
        count += 1

    return days + day + hour / 24 + minute / 1440 + second / 86400


def getTargetJulianDate(start_julian_date, jump_delta):
    """Determine the final Julian date for the simulation.

    Args:
        start_julian_date (:class:`.JulianDate`): Julian date at simulation start
        jump_delta (`datetime.timedelta`): amount of time to simulate

    Returns:
        :class:`.JulianDate`: Julian date at simulation stop
    """
    if not isinstance(start_julian_date, JulianDate):
        start_julian_date = JulianDate(start_julian_date)

    if not isinstance(jump_delta, datetime.timedelta):
        resonaateLogError("Error: `jump_delta` must be a `datetime.timedelta` object.")
        raise TypeError(type(jump_delta))

    start_calendar_date = julianDateToDatetime(start_julian_date)
    target_calendar_date = start_calendar_date + jump_delta

    return JulianDate.getJulianDate(
        target_calendar_date.year,
        target_calendar_date.month,
        target_calendar_date.day,
        target_calendar_date.hour,
        target_calendar_date.minute,
        target_calendar_date.second,
    )
