# Standard Library Imports
# Third Party Imports
from numpy import sqrt, dot, arccos, arcsin
from scipy.linalg import norm
# RESONAATE Imports
from ..physics import constants as const
from ..physics.bodies import Earth
from ..physics.bodies.third_body import Sun


def getObscurAngle(eci_state):
    """Return the elevation angle between tgt and the limb of the Earth.

    Determine the cone angle that the satellite makes with Earth's limb, which we define as the
    radius of the Earth plus 100 km

    Args;
        eci_state (``np.ndarray``): 6x1 ECI state vector of the satellite (km; km/sec)

    Returns:
        ``float``: angle target makes with the Earth's limb in radians, [-pi/2, 0]
    """
    return arcsin((Earth.radius + Earth.atmosphere) / norm(eci_state[:3])) - const.PI * 0.5


def lineOfSight(eci_position_1, eci_position_2):
    """Determine if line of sight exists between two given positions.

    See Vallado Algorithm 35 for details. This assumes a spherical Earth which is more
    conservative.

    References:
        "Fundamentals of Astrodynamics and Applications", David Vallado, Fourth Edition, 2013.

    Args:
        eci_position_1 (``np.ndarray``): 3x1 ECI position vector 1, km
        eci_position_2 (``np.ndarray``): 3x1 ECI position vector 2, km

    Returns:
        ``bool``: whether a line of sight exists between the given position vectors.
    """
    r1_dot_r2 = dot(eci_position_1, eci_position_2)
    r1sq, r2sq = norm(eci_position_1)**2, norm(eci_position_2)**2
    tau = (r1sq - r1_dot_r2) / (r1sq + r2sq - 2 * r1_dot_r2)
    if tau < 0.0 or tau > 1.0:
        return True
    else:
        return (1 - tau) * r1sq + r1_dot_r2 * tau >= Earth.radius**2


def calculateSunVizFraction(tgt_eci_position, sun_eci_position):
    """Calculate the fraction of the Sun __NOT__ occluded by Earth from a satellite's position.

    See Montenbruck section 3.42 for an explanation & derivation. This method is only valid for
    orbiting satellites.

    References:
        "Satellite Orbits: Models, Methods and Applications", Oliver Montenbruck, 2000.

    Args:
        tgt_eci_position (``np.ndarray``): 3X1 ECI position vector of satellite
        sun_eci_position (``np.ndarray``): 3x1 ECI position vector of the Sun, relative to Earth (km)

    Returns:
        ``float``: percentage of the Sun that is visible from the satellite
    """
    # pylint: disable=invalid-name
    sat_sun_vector = sun_eci_position - tgt_eci_position

    # Montenbruck, Eqs. 3.85 to 3.87
    a = arcsin(Sun.radius / norm(sat_sun_vector))
    b = arcsin(Earth.radius / norm(tgt_eci_position))
    c = arccos(dot(-tgt_eci_position, sat_sun_vector) / (norm(tgt_eci_position) * norm(sat_sun_vector)))

    # [TODO]: Determine if the `AND`s are required. Does the algorithm include when sat in front of Earth?
    if c < abs(b - a) and norm(sun_eci_position) < norm(sat_sun_vector):
        return 0
    elif c < abs(a + b) and norm(sun_eci_position) < norm(sat_sun_vector):
        # Montenbruck Eq. 3.93
        x = (c**2 + a**2 - b**2) / (2 * c)
        y = sqrt(a**2 - x**2)

        # Montenbruck Eqs. 3.92 & 3.94
        A = a**2 * arccos(x / a) + b**2 * arccos((c - x) / b) - c * y

        # Partial occultation
        return 1.0 - A / (const.pi * a**2)
    else:
        return 1  # No occultation by the Earth


def calculateIncidentSolarFlux(viz_cross_section, tgt_eci_position, sun_eci_position):
    """Calculate the current solar flux of a target object.

    References:
        Autonomous and Responsive Surveillance Network Management for Adaptive Space Situational Awareness,
        Kevin M. Nastasi. 8 June 2018. page 47, equation 3.10

    Args:
        viz_cross_section (``float``): area of the target facing the sun (m^2)
        tgt_eci_position (``np.ndarray``): 3x1 ECI position vector of the target (km)
        sun_eci_position (``np.ndarray``): 3x1 ECI position vector of the Sun, relative to Earth (km)

    Returns:
        ``float``: incident solar flux (W)
    """
    solar_flux = const.SOLAR_FLUX * viz_cross_section
    return solar_flux * calculateSunVizFraction(tgt_eci_position, sun_eci_position)


def checkGroundSensorLightingConditions(sensor_eci_position, sun_eci_vector, buffer_angle=const.PI / 12):
    """Determine if a ground sensor has the appropriate lighting condition.

    This assumes ground-based sensors can only collect during times of eclipse (nighttime). There
    is also an optional buffer added on for excluding dusk/dawn hours. The lighting condition is
    valid as long as the satellite-sun angle is greater than 90 degrees plus the buffer angle.

    Args:
        sensor_eci_position (``np.ndarray``): 3x1 ECI position vector of the sensor object (km)
        sun_eci_vector (``np.ndarray``): 3x1 ECI unit vector of the Sun, relative to the Earth
        buffer_angle (``float``, optional): angle to add to eclipse condition to account for
            dusk/dawn (radians). Defaults to 15 degrees.

    Returns:
        ``bool``: whether the sensor can view objects or not based on the lighting condition.
    """
    satellite_sun_angle = arccos(dot(sun_eci_vector, sensor_eci_position) / norm(sensor_eci_position))
    return satellite_sun_angle >= const.PI / 2 + buffer_angle


def checkSpaceSensorLightingConditions(boresight_eci_vector, sun_eci_vector, cone_angle=const.PI / 12):
    """Determine if a space sensor has the appropriate lighting condition.

    This assumes space-based sensors can only collect if the required boresight vector is not
    pointing to within a specified cone angle of the sun. The lighting condition is
    valid as long as the boresight-sun angle is greater than the cone angle.

    Args:
        boresight_eci_vector (``np.ndarray``): 3x1 ECI boresight vector from the sensor to the target (km)
        sun_eci_vector (``np.ndarray``): 3x1 ECI unit vector of the Sun, relative to the Earth
        cone_angle (``float``, optional): minimum cone angle the sensor can have with the sun
            (radians). Defaults to 15 degrees.

    Returns:
        ``bool``: whether the sensor can view objects or not based on the lighting condition.
    """
    boresight_sun_angle = arccos(dot(sun_eci_vector, boresight_eci_vector) / norm(boresight_eci_vector))
    return boresight_sun_angle >= cone_angle


def calculateRadarCrossSection(viz_cross_section, wavelength):
    """Calculate the effective area seen by a radar signal.

    This equation assumes radar is reflected perpendicualary from a flat plat and
    returns the maximum possible cross section

    References:
        Autonomous and Responsive Surveillance Network Management for Adaptive Space Situational Awareness,
        Kevin M. Nastasi. 8 June 2018. page 46, equation 3.5

    Args:
        viz_cross_section (``float``): area of the object facing the signal (m^2)
        wavelength (``float``): wavelength of the signal (m)

    Returns:
        ``float``: effective cross-sectional area (m^2)
    """
    return 4 * const.PI * viz_cross_section ** 2 / wavelength ** 2


def getWavelengthFromString(freq):
    """Return the wavelength of the given frequency band.

    Args:
        freq (``str``): frequency band to get the wavelength of

    Returns:
        ``float``: wavelength of the given frequency band (m)
    """
    return {
        'VHF': const.SPEED_OF_LIGHT / (165.0 * (1e6)),
        'UHF': const.SPEED_OF_LIGHT / (650.0 * (1e6)),
        'L': const.SPEED_OF_LIGHT / (1.5 * (1e9)),
        'S': const.SPEED_OF_LIGHT / (3.0 * (1e9)),
        'C': const.SPEED_OF_LIGHT / (6.0 * (1e9)),
        'X': const.SPEED_OF_LIGHT / (10.0 * (1e9)),
        'Ku': const.SPEED_OF_LIGHT / (15.0 * (1e9)),
        'K': const.SPEED_OF_LIGHT / (20.0 * (1e9)),
        'Ka': const.SPEED_OF_LIGHT / (30.0 * (1e9)),
        'V': const.SPEED_OF_LIGHT / (60.0 * (1e9)),
        'W': const.SPEED_OF_LIGHT / (15.0 * (1e9)),
    }[freq]
