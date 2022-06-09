# Standard Library Imports
# Third Party Imports
from numpy import dot, matmul, asarray, sum as np_sum, empty_like
from numpy.linalg import multi_dot
from scipy.linalg import norm
# RESONAATE Imports
from .constants import RK45_LABEL
from .celestial import Celestial, checkEarthCollision
from ..physics import constants as const
from ..physics.bodies import Earth, Moon, Sun
from ..physics.bodies.third_body import getThirdBodyPositions
from ..physics.math import rot3
from ..physics.sensor_utils import calculateSunVizFraction
from ..physics.time.conversions import dayOfYear, greenwichApparentTime
from ..physics.time.stardate import JulianDate
from ..physics.transforms.reductions import getReductionParameters


class SpecialPerturbations(Celestial):
    """SpecialPerturbations class.

    Implements the Dynamics abstract class to enable propagation of the state vector (in the ECI
    reference frame) using the Special Perturbations method of numerical integration.
    """

    def __init__(self, jd_start, geopotential, perturbations, method=RK45_LABEL):
        """Construct a SpecialPerturbations object.

        Args:
            jd_start (:class:`.JulianDate`): Julian date of the scenario's initial epoch
            geopotential (GeopotentialConfig): config describing the geopotential model and the accuracy
            perturbations (PerturbationsConfig): config describing which perturbations to include
            method (``str``, optional): Defaults to ``'RK45'``. Which ODE integration method to use
        """
        super(SpecialPerturbations, self).__init__(method=method)
        self.init_julian_date = jd_start
        self.earth_model = Earth(geopotential.model)
        self.degree = geopotential.degree
        self.order = geopotential.order
        self.third_bodies = thirdBodyFactory(perturbations.third_bodies)
        self._method = method

    def _differentialEquation(self, time, state):
        """Calculate the first time derivative of the state for numerical integration.

        Note: this function must take and receive 1-dimensional state vectors! Also, `K` below
            refers to the number of parallel integrations being performed

        Args:
            time (:class:`.ScenarioTime`): the current time of integration, (seconds)
            state (``numpy.ndarray``): (6 * K, ) current state vector in integration, (km, km/sec)

        Returns:
            ``numpy.ndarray``: (6 * K, ) derivative of the state vector, (km/sec; km/sec^2)
        """
        # Determine the step and halfway point for each vector
        step = int(state.shape[0] / 6)
        half = int(state.shape[0] / 2)
        derivative = empty_like(state, dtype=float)

        # Calculate the ECI - ECEF transformation for the integration time
        julian_date = JulianDate(self.init_julian_date + time / 86400)
        ecef_2_eci = _getRotationMatrix(julian_date, getReductionParameters())

        # Get third body positions
        positions = {body: getThirdBodyPositions()[name] for body, name in self.third_bodies.items()}
        for jj in range(step):
            # pylint: disable=unsupported-assignment-operation

            # Determine the position vectors in J2000 frame
            r_eci = state[jj:jj + half:step]

            # Check if an RSO crashed into the Earth
            checkEarthCollision(norm(r_eci))

            # Get ECEF position
            r_ecef = matmul(ecef_2_eci.T, r_eci)

            # Non-spherical gravity acceleration
            a_nonspherical = matmul(
                ecef_2_eci,
                self.earth_model.nonSphericalGeopotential(r_ecef, self.degree, self.order)
            )

            # Third body accelerations
            a_third_body = np_sum(
                [body.mu * _getThirdBodyAcceleration(r_eci, position) for body, position in positions.items()],
                axis=0
            )

            # Solar Radiation Pressure accelerations
            a_srp = _getSolarRadiationPressureAcceleration(r_eci)

            # Add all the perturbations together
            a_perturbations = a_nonspherical + a_third_body + a_srp

            # Save state derivative for this state vector
            derivative[jj:jj + half:step] = state[jj + half::step]
            derivative[jj + half::step] = -1. * Earth.mu / (norm(r_eci)**3.0) * r_eci + a_perturbations

        return derivative


def _getRotationMatrix(julian_date, reduction):
    """Determine the current ECEF -> ECI rotation matrix.

    Args:
        julian_date (:class:`.JulianDate`): Julian date of the current rotation

    Returns:
        ``numpy.ndarray``: (3, 3) rotation matrix
    """
    # Convert year and epoch to mdhms form. Time always in UTC
    year, month, day, hours, minutes, seconds = julian_date.calendar_date
    elapsed_days = dayOfYear(year, month, day, hours, minutes, seconds + reduction["dut1"]) - 1
    greenwich_apparent_sidereal_time = greenwichApparentTime(year, elapsed_days, reduction["eq_equinox"])
    return multi_dot(
        [reduction["rot_pn"], rot3(-1.0 * greenwich_apparent_sidereal_time), reduction["rot_w"]]
    )


def _getThirdBodyAcceleration(sat_position, third_body_position):
    """Determine the acceleration of a satellite due to a third body.

    See Vallado Ed. 4, Section 8.6.3, Eq

    Args:
        sat_position (``numpy.ndarray``): (3, ) ECI position vector of the satellite, (km)
        third_body_position (``numpy.ndarray``): (3, ) ECI position vector of the third body object, (km)

    Returns:
        `np::ndarray`: (3, ) un-scaled ECI acceleration term due to the third body object, (1/km^2)
    """
    # Position of the satellite, relative to Earth
    r_e_sat = sat_position
    r_e_sat_norm = norm(r_e_sat)
    # Position of the third body, relative to Earth
    r_e_3 = third_body_position
    r_e_3_norm = norm(r_e_3)
    # Position of the third body, relative to the satellite
    r_sat_3 = third_body_position - sat_position
    r_sat_3_norm = norm(r_sat_3)

    # Convenient intermediate term
    denominator = (r_e_sat_norm**2 + 2 * dot(r_e_sat, r_sat_3)) *\
                  (r_e_3_norm**2 + r_e_3_norm * r_sat_3_norm + r_sat_3_norm**2)
    q_3 = denominator / (r_e_3_norm**3 * r_sat_3_norm**3 * (r_e_3_norm + r_sat_3_norm))

    # Compile the un-scaled acceleration
    acceleration = r_sat_3 * q_3 - (r_e_sat / (r_e_3_norm**3))

    return acceleration


def thirdBodyFactory(configuration):
    """Create third body perturbations based on a config.

    Args:
        configuration (list(str)): names of third bodies to include

    Returns:
        dict: third body position function multi-dispatch dict
    """
    third_bodies = {}
    for body in configuration:
        if body.lower() == "sun":
            third_bodies[Sun] = "sun"
        elif body.lower() == "moon":
            third_bodies[Moon] = "moon"
        else:
            raise ValueError("Incorrect option for 'third_bodies' in config: {0}".format(
                body
            ))

    return third_bodies


def _getSolarRadiationPressureAcceleration(sat_position):
    """Calculate the acceleration on the spacecraft due to solar radiation pressure.

    TODO:
        - Remove hardcoded constants

    References:
        "Satellite Orbits: Models, Methods and Applications", Oliver Montenbruck, 2000.

    Args:
        sat_position (`np.ndarray`): 3X1 ECI position vector of the satellite

    Returns:
        `np.ndarray`: 3X1 ECI acceleration vector due to SRP, km/s^2
    """
    # Satellite Constants
    viz_cross_section = 25.0  # (m^2)
    mass = 150.0  # Satellite mass (kg)
    # Assuming solar panel reflectivity where epsilon = 0.21 (Montenbruck, Table 3.5)
    c_r = 1.21  # Radiation Pressure Coefficient (1 + epsilon) (Montenbruck, Eq. 3.76)
    sat_ratio = c_r * (viz_cross_section / mass)  # combine into single variable for simpler code

    sun_position = asarray(getThirdBodyPositions()["sun"])
    # Vector from satellite to the Sun
    position = sun_position - sat_position
    # SRP acceleration in m/s^2, Montenbruck Eq. 3.75, modified
    a_srp = -const.SOLAR_PRESSURE * sat_ratio * (const.AU2KM / norm(position))**2 * position / norm(position)

    # Multiply SRP acceleration by the percentage of the Sun that is visible, convert to km/s^2
    return a_srp * calculateSunVizFraction(sat_position, sun_position) / 1000.0
