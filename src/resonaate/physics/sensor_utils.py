"""Functions that define physics related to sensors."""
from __future__ import annotations

# Standard Library Imports
from typing import TYPE_CHECKING

# Third Party Imports
from numpy import arccos, arcsin, cos, dot, log10, sin, sqrt
from scipy.linalg import norm

# Local Imports
from .bodies import Earth
from .bodies.third_body import Sun
from .constants import DEG2RAD, PI, SOLAR_FLUX, SPEED_OF_LIGHT
from .maths import subtendedAngle
from .transforms.methods import spherical2cartesian

if TYPE_CHECKING:
    # Third Party Imports
    from numpy import ndarray


GALACTIC_BELT_ECI = spherical2cartesian(
    rho=2.46e17,
    theta=-29.007805555555555556 * DEG2RAD,
    phi=4.649850924403647,
    rho_dot=0.0,
    theta_dot=0.0,
    phi_dot=0.0,
)


def getEarthLimbConeAngle(eci_state: ndarray) -> float:
    r"""Return the elevation angle between a sensor and the limb of the Earth.

    Determine the cone angle that the satellite makes with Earth's limb, which we define as the
    radius of the Earth plus the height of the atmosphere.

    The limb angle will always be in :math:`[-\frac{\pi}{2}, 0]` for satellites, because elevation is
    measured from the local SE plane in the SEZ system to the Z axis which points radially
    outward, along the ECI position direction. Therefore, the sensor's limb angle will always
    be negative.

    References:
        :cite:t:`nastasi_2018_scitech_dst`, Section II.C.3

    Args:
        eci_state (``ndarray``): 6x1 ECI state vector of the sensor satellite (km; km/s)

    Returns:
        ``float``: angle target makes with the Earth's limb, :math:`[-\frac{\pi}{2}, 0]` (rad)
    """
    return arcsin((Earth.radius + Earth.atmosphere) / norm(eci_state[:3])) - PI * 0.5


def lineOfSight(eci_position_1: ndarray, eci_position_2: ndarray) -> bool:
    r"""Determine if line of sight exists between two given positions.

    This assumes a spherical Earth which is more conservative.

    References:
        :cite:t:`vallado_2013_astro`, Algorithm 35

    Args:
        eci_position_1 (``ndarray``): 3x1 ECI position vector 1 (km)
        eci_position_2 (``ndarray``): 3x1 ECI position vector 2 (km)

    Returns:
        ``bool``: whether a line of sight exists between the given position vectors.
    """
    r1_dot_r2 = dot(eci_position_1, eci_position_2)
    r1sq, r2sq = norm(eci_position_1) ** 2, norm(eci_position_2) ** 2
    tau = (r1sq - r1_dot_r2) / (r1sq + r2sq - 2 * r1_dot_r2)
    if tau < 0.0 or tau > 1.0:
        return True

    return (1 - tau) * r1sq + r1_dot_r2 * tau >= Earth.radius**2


def calculateSunVizFraction(tgt_eci_position: ndarray, sun_eci_position: ndarray) -> float:
    r"""Calculate the fraction of the Sun **NOT** occluded by Earth from a satellite's position.

    This method is only valid for orbiting satellites. See the last paragraph of section 3.4 in
    "Satellite Orbits" by Montenbruck for explanation of the occultation conditions.

    References:
        :cite:t:`montenbruck_2012_orbits`, Section 3.42

    Args:
        tgt_eci_position (``ndarray``): 3x1 ECI position vector of satellite (km)
        sun_eci_position (``ndarray``): 3x1 ECI position vector of the Sun, relative to Earth (km)

    Returns:
        ``float``: percentage of the Sun that is visible from the satellite
    """
    # pylint: disable=invalid-name
    sat_sun_vector = sun_eci_position - tgt_eci_position

    # Montenbruck, Eqs. 3.85 to 3.87
    a = arcsin(Sun.radius / norm(sat_sun_vector))
    b = arcsin(Earth.radius / norm(tgt_eci_position))
    c = arccos(
        dot(-tgt_eci_position, sat_sun_vector) / (norm(tgt_eci_position) * norm(sat_sun_vector))
    )

    # No occultation is possible if the satellite is closer to the Sun than the ECI origin
    if norm(sun_eci_position) >= norm(sat_sun_vector):
        return 1.0

    # Full occultation, see Eqn 3.89
    if c < abs(b - a):
        return 0.0

    # Partial occultation, see Eqn 3.89
    if c < abs(a + b):
        # Montenbruck Eq. 3.93
        x = (c**2 + a**2 - b**2) / (2 * c)
        y = sqrt(a**2 - x**2)

        # Montenbruck Eqs. 3.92 & 3.94
        A = a**2 * arccos(x / a) + b**2 * arccos((c - x) / b) - c * y

        # Partial occultation
        return 1.0 - A / (PI * a**2)

    return 1.0  # No occultation by the Earth


def calculateIncidentSolarFlux(
    viz_cross_section: float, tgt_eci_position: ndarray, sun_eci_position: ndarray
) -> float:
    r"""Calculate the current solar flux of a target object.

    References:
        :cite:t:`nastasi_2018_diss`, Pg 47, Eqn 3.10

    Args:
        viz_cross_section (``float``): area of the target facing the sun (m\ :sup:`2`)
        tgt_eci_position (``ndarray``): 3x1 ECI position vector of the target (km)
        sun_eci_position (``ndarray``): 3x1 ECI position vector of the Sun, relative to Earth (km)

    Returns:
        ``float``: incident solar flux (W)
    """
    solar_flux = SOLAR_FLUX * viz_cross_section
    return solar_flux * calculateSunVizFraction(tgt_eci_position, sun_eci_position)


def checkGroundSensorLightingConditions(
    sensor_eci_position: ndarray, sun_eci_unit_vector: ndarray, buffer_angle: float = PI / 12
) -> bool:
    r"""Determine if a ground sensor has the appropriate lighting condition.

    This assumes ground-based sensors can only collect during times of eclipse (nighttime). There
    is also an optional buffer added on for excluding dusk/dawn hours. The lighting condition is
    valid as long as the satellite-sun angle is greater than 90 degrees plus the buffer angle.

    References:
        :cite:t:`vallado_2013_astro`, Section 5.3.2, Eqn 5-2

    Args:
        sensor_eci_position (``ndarray``): 3x1 ECI position vector of the sensor object (km)
        sun_eci_unit_vector (``ndarray``): 3x1 ECI unit position vector of the Sun, relative to the Earth (km)
        buffer_angle (``float``, optional): angle to add to eclipse condition to account for
            dusk/dawn (rad). Defaults to :math:`\frac{\pi}{12}`.

    Returns:
        ``bool``: whether the sensor can view objects or not based on the lighting condition.
    """
    satellite_sun_angle = arccos(
        dot(sun_eci_unit_vector, sensor_eci_position) / norm(sensor_eci_position)
    )
    return satellite_sun_angle >= PI / 2 + buffer_angle


def checkSpaceSensorLightingConditions(
    boresight_eci_vector: ndarray, sun_eci_unit_vector: ndarray, cone_angle: float = PI / 12
) -> bool:
    r"""Determine if a space sensor has the appropriate lighting condition.

    This assumes space-based sensors can only collect if the required boresight vector is not
    pointing to within a specified cone angle of the sun. The lighting condition is
    valid as long as the boresight-sun angle is greater than the cone angle.

    References:
        :cite:t:`vallado_2013_astro`, Section 5.3.2, Eqn 5-2 (modified for space sensors)

    Args:
        boresight_eci_vector (``ndarray``): 3x1 ECI boresight vector from the sensor to the target (km)
        sun_eci_unit_vector (``ndarray``): 3x1 ECI unit position vector of the Sun, relative to the Earth (km)
        cone_angle (``float``, optional): minimum cone angle the sensor can have with the sun
            (rad). Defaults to :math:`\frac{\pi}{12}`.

    Returns:
        ``bool``: whether the sensor can view objects or not based on the lighting condition.
    """
    boresight_sun_angle = arccos(
        dot(sun_eci_unit_vector, boresight_eci_vector) / norm(boresight_eci_vector)
    )
    return boresight_sun_angle >= cone_angle


def calculateRadarCrossSection(viz_cross_section: float, wavelength: float) -> float:
    r"""Calculate the effective area seen by a radar signal.

    This equation assumes radar is reflected perpendicularly from a flat plat and
    returns the maximum possible cross section.

    References:
        :cite:t:`nastasi_2018_diss`, Pg 46, Eqn 3.5

    Args:
        viz_cross_section (``float``): area of the object facing the signal (m\ :sup:`2`)
        wavelength (``float``): wavelength of the signal (m)

    Returns:
        ``float``: effective cross-sectional area (m\ :sup:`2`)
    """
    return 4 * PI * viz_cross_section**2 / wavelength**2


def getWavelengthFromString(freq: str):
    r"""Return the wavelength of the given frequency band.

    Args:
        freq (``str``): frequency band to get the wavelength of

    Returns:
        ``float``: wavelength of the given frequency band (m)
    """
    return {
        "VHF": SPEED_OF_LIGHT / (165.0 * (1e6)),
        "UHF": SPEED_OF_LIGHT / (650.0 * (1e6)),
        "L": SPEED_OF_LIGHT / (1.5 * (1e9)),
        "S": SPEED_OF_LIGHT / (3.0 * (1e9)),
        "C": SPEED_OF_LIGHT / (6.0 * (1e9)),
        "X": SPEED_OF_LIGHT / (10.0 * (1e9)),
        "Ku": SPEED_OF_LIGHT / (15.0 * (1e9)),
        "K": SPEED_OF_LIGHT / (20.0 * (1e9)),
        "Ka": SPEED_OF_LIGHT / (30.0 * (1e9)),
        "V": SPEED_OF_LIGHT / (60.0 * (1e9)),
        "W": SPEED_OF_LIGHT / (15.0 * (1e9)),
    }[freq]


def apparentVisualMagnitude(
    visual_cross_section: float, reflectivity: float, phase_function: float, rso_range: float
) -> float:
    """Calculate apparent visual magnitude of an RSO.

    Args:
        visual_cross_section (``float, int``): constant visual cross-section of the agent
        reflectivity (``float``): constant reflectivity of the agent
        phase_function (``float``): solar phase of RSO
        rso_range (``float``): range from sensor to RSO

    Returns:
        ``float``: apparent visual magnitude (unitless)

    References:
        :cite:t:`cognion_2013_amos`, Eqn 3
    """
    vcs_km2 = visual_cross_section * 1e-6
    return Sun.absolute_magnitude - 2.5 * log10(
        (vcs_km2 * reflectivity * phase_function) / rso_range**2
    )


def lambertianPhaseFunction(phi: float) -> float:
    """Reflection off a spherical Lambertian reflector.

    Args:
        phi (``float``): phase angle

    Returns
        (``float``): phase angle

    References:
        :cite:t:`cognion_2013_amos`, Eqn 1
    """
    return 2 * ((PI - phi) * cos(phi) + sin(phi)) / (3 * PI**2)


def calculatePhaseAngle(emitter: ndarray, reflector: ndarray, observer: ndarray) -> float:
    """Angle between the light incident onto an observed object and the light reflected from the object.

    Args:
        emitter (``ndarray``): 3x1 ECI position of emitting body
        reflector (``ndarray``): 3x1 ECI position reflection body
        observer (``ndarray``): 3x1 ECI position of observer

    Returns:
        ``float``: angle between the light incident onto an observed object and the light reflected from the object
    """
    phase_angle = subtendedAngle(
        emitter - reflector,
        observer - reflector,
    )

    return phase_angle


def checkGalacticExclusionZone(boresight_eci_vector, cone_angle=PI / 30):
    """Determine if a sensor has appropriate lighting conditions.

    RA 17h 45m 40.04s (radians: 4.649850924403647),
    Dec -29° 00` 28.1″ (degrees: -29.007805555555555556)
    range ~26 kilolight-years
    """
    boresight_belt_angle = arccos(
        dot(GALACTIC_BELT_ECI[:3], boresight_eci_vector)
        / (norm(GALACTIC_BELT_ECI[:3]) * norm(boresight_eci_vector))
    )
    return boresight_belt_angle >= cone_angle
