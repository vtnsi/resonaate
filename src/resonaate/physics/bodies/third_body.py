"""Third Body Module.

Provides classes for third bodies utilized in Resonaate. The classes implement
JPL Horizons data to provide extremely accurate state data for Solar System
bodies.

See Also:
    https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/planets/ for more information on the binary files.
"""
# Standard Library Imports
from pickle import dumps, loads
from pkg_resources import resource_filename
# Third Party Imports
from numpy import asarray
from jplephem.spk import SPK
# RESONAATE Imports
from ...parallel import getRedisConnection


# Load the binary JPL Horizons kernel file
KERNEL_FILE = resource_filename('resonaate', 'physics/data/de432s.bsp')
"""jplephem.spk.SPK: object that allows querying of JPL binary data file."""


THIRD_BODY_REDIS_KEY = "third_body"
"""str: Redis key used to store third body positions."""


def updateThirdBodyPositions(julian_date, third_bodies):
    """Update the current set of third body positions in GCRF.

    Args:
        julian_date (`JulianDate`): Julian date to calculate the transformation for
    """
    param_dict = {name: body.getPosition(julian_date) for name, body in third_bodies.items()}
    param_dict["julian_date"] = julian_date

    getRedisConnection().set(THIRD_BODY_REDIS_KEY, dumps(param_dict))


def getThirdBodyPositions():
    """Retrieve current set of third body positions in GCRF from Redis.

    Note:
        :meth:`.updateThirdBodyPositions()` *must* be called before this function.

    Raises:
        ValueError: If :meth:`.updateThirdBodyPositions()` hasn't been previously called to set
            the third body positions in GCRF.

    Returns:
        numpy::ndarray: 3x1 GCRF position vector of the body's center in km
    """
    serial_obj = getRedisConnection().get(THIRD_BODY_REDIS_KEY)

    if serial_obj is None:
        raise ValueError("Third body positions have not been updated.")

    return loads(serial_obj)


class Sun:
    """Sun third body class.

    See Also:
     Vallado Ed. 4, Appendix D.3, Table D-5.
    """

    mu = 1.32712428e11
    """float: gravitational parameter, (km^3/sec^2)."""
    radius = 696000.0
    """float: mean equatorial radius (km)."""
    mass = 1.9891e30
    """float: planet's mass, (km)."""
    position = None
    """``numpy.ndarray``: 3x1 ECI position vector, (km)."""

    @staticmethod
    def getPosition(julian_date):
        """Calculate the :class:`.Sun`'s position vector, relative to :class:`.Earth`.

        Args:
            julian_date (JulianDate): time to query for the :class:`.Sun`'s position

        Returns:
            numpy::ndarray: 3x1 GCRF position vector of the :class:`.Sun`'s center, (km)
        """
        kernel = SPK.open(KERNEL_FILE)
        # Create relative position vector from Earth to the Sun
        position = kernel[0, 10].compute(julian_date)  # SS BC to Sun center
        position -= kernel[0, 3].compute(julian_date)  # SS BC to Earth BC
        position -= kernel[3, 399].compute(julian_date)  # Earth BC to Earth Center
        kernel.close()

        return asarray(position)


class Moon:
    """Moon third body class.

    See Also:
     Vallado Ed. 4, Appendix D.3, Table D-3.
    """

    mu = 4902.799
    """float: gravitational parameter, (km^3/sec^2)."""
    radius = 1738.0
    """float: mean equatorial radius (km)."""
    mass = 7.3483e22
    """float: planet's mass, (km)."""
    position = None
    """``numpy.ndarray``: 3x1 ECI position vector, (km)."""

    @staticmethod
    def getPosition(julian_date):
        """Calculate the :class:`.Moon`'s position vector, relative to :class:`.Earth`.

        Args:
            julian_date (JulianDate): time to query for the :class:`.Moon`'s position

        Returns:
            numpy::ndarray: 3x1 GCRF position vector of the :class:`.Moon`'s center, (km)
        """
        kernel = SPK.open(KERNEL_FILE)
        # Create relative position vector from Earth to the Moon
        position = kernel[3, 301].compute(julian_date)  # SS BC to Earth BC
        position -= kernel[3, 399].compute(julian_date)  # Earth BC to Moon center
        kernel.close()

        return asarray(position)
