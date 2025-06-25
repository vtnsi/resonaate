"""Defines the :class:`.SpecialPerturbations` class for high fidelity astrodynamics models."""

from __future__ import annotations

# Standard Library Imports
from typing import TYPE_CHECKING

# Third Party Imports
from numpy import array, concatenate, cross, empty_like, matmul
from numpy import sum as np_sum
from numpy import vdot
from numpy.linalg import multi_dot
from scipy.linalg import norm

# Local Imports
from ..common.labels import IntegratorLabel
from ..physics import constants as const
from ..physics.bodies import Earth, Jupiter, Moon, Saturn, Sun, Venus
from ..physics.bodies.gravitational_potential import (
    loadGeopotentialCoefficients,
    nonSphericalAcceleration,
)
from ..physics.maths import rot3
from ..physics.sensor_utils import calculateSunVizFraction
from ..physics.time.conversions import dayOfYear, greenwichApparentTime
from ..physics.time.stardate import JulianDate, julianDateToDatetime
from ..physics.transforms.reductions import ReductionParams
from .celestial import Celestial, checkEarthCollision

if TYPE_CHECKING:
    # Third Party Imports
    from numpy import ndarray

    # Local Imports
    from ..physics.time.stardate import ScenarioTime
    from ..scenario.config.geopotential_config import GeopotentialConfig
    from ..scenario.config.perturbations_config import PerturbationsConfig


class SpecialPerturbations(Celestial):
    """SpecialPerturbations class.

    Implements the Dynamics abstract class to enable propagation of the state vector (in the ECI
    reference frame) using the Special Perturbations method of numerical integration.
    """

    def __init__(
        self,
        jd_start: JulianDate,
        geopotential: GeopotentialConfig,
        perturbations: PerturbationsConfig,
        sat_ratio: float,
        method: str = IntegratorLabel.RK45,
    ):
        """Construct a SpecialPerturbations object.

        Args:
            jd_start (:class:`.JulianDate`): Julian date of the scenario's initial epoch
            geopotential (:class:`.GeopotentialConfig`): config describing the geopotential model and the accuracy
            perturbations (:class:`.PerturbationsConfig`): config describing which perturbations to include
            sat_ratio (``float``): area-to-mass ratio times the coefficient of solar radiation pressure, see :func:.calculateSatRatio for details.
            method (``str``, optional): Defaults to ``'RK45'``. Which ODE integration method to use
        """
        super().__init__(method=method)
        self.init_julian_date = jd_start
        self.c_nm, self.s_nm = loadGeopotentialCoefficients(geopotential.model)
        self.degree = geopotential.degree
        self.order = geopotential.order
        self.third_bodies = thirdBodyFactory(perturbations.third_bodies)
        self.use_srp = perturbations.solar_radiation_pressure
        self.sat_ratio = sat_ratio
        self.use_gr = perturbations.general_relativity

    def _differentialEquation(
        self,
        time: ScenarioTime,
        state: ndarray,
        check_collision: bool = True,
    ) -> ndarray:
        """Calculate the first time derivative of the state for numerical integration.

        Uses Cowell's formulation.

        References:
            :cite:t:`vallado_2013_astro`, Section 8.6.3, Eqn 8-3

        Note: this function must take and receive 1-dimensional state vectors! Also, `K` below
            refers to the number of parallel integrations being performed

        Args:
            time (:class:`.ScenarioTime`): the current time of integration, (seconds)
            state (``ndarray``): (6 * K, ) current state vector in integration, (km, km/sec)
            check_collision (``bool``): whether to error on collision with the primary body

        Returns:
            ``ndarray``: (6 * K, ) derivative of the state vector, (km/sec; km/sec^2)
        """
        # Determine the step and halfway point for each vector
        step = int(state.shape[0] / 6)
        half = int(state.shape[0] / 2)
        derivative = empty_like(state, dtype=float)

        # Calculate the ECI - ECEF transformation for the integration time
        julian_date = JulianDate(self.init_julian_date + time / 86400)
        _datetime = julianDateToDatetime(julian_date)
        ecef_2_eci = _getRotationMatrix(julian_date, ReductionParams.build(_datetime))

        # Get third body positions
        positions = {body: body.getPosition(julian_date) for body in self.third_bodies}

        # Set sun position for SRP
        sun_positions = (
            Sun.getPosition(julian_date) if Sun not in self.third_bodies else positions[Sun]
        )

        for jj in range(step):
            # Determine the position vectors in J2000 frame
            r_eci = state[jj : jj + half : step]

            # Determine the velocity vectors in J2000 frame
            v_eci = state[jj + half :: step]

            if check_collision:
                # Check if an RSO crashed into the Earth
                checkEarthCollision(norm(r_eci))

            # Get ECEF position
            r_ecef = matmul(ecef_2_eci.T, r_eci)

            # Non-spherical gravity acceleration
            a_nonspherical = matmul(
                ecef_2_eci,
                nonSphericalAcceleration(
                    r_ecef,
                    Earth.mu,
                    Earth.radius,
                    self.c_nm,
                    self.s_nm,
                    self.degree,
                    self.order,
                ),
            )

            # Third body accelerations
            a_third_body = np_sum(
                [
                    body.mu * _getThirdBodyAcceleration(r_eci, position)
                    for body, position in positions.items()
                ],
                axis=0,
            )

            # Solar Radiation Pressure accelerations
            a_srp = (
                self._getSolarRadiationPressureAcceleration(r_eci, array(sun_positions))
                if self.use_srp
                else 0.0
            )

            # General Relativity accelerations
            a_gr = _getGeneralRelativityAcceleration(r_eci, v_eci) if self.use_gr else 0.0

            # Add all the perturbations together
            a_perturbations = a_nonspherical + a_third_body + a_srp + a_gr
            # Add thrust acceleration if applicable
            if self.finite_thrust:
                a_perturbations += self.finite_thrust(concatenate((r_eci, v_eci)))[:3]

            # Save state derivative for this state vector
            derivative[jj : jj + half : step] = state[jj + half :: step]
            derivative[jj + half :: step] = (
                -1.0 * Earth.mu / (norm(r_eci) ** 3.0) * r_eci + a_perturbations
            )

        return derivative

    def _getSolarRadiationPressureAcceleration(
        self,
        sat_position: ndarray,
        sun_eci_position: ndarray,
    ) -> ndarray:
        """Calculate the acceleration on the spacecraft due to solar radiation pressure.

        Args:
            sat_position (``ndarray``): 3x1 ECI position vector of the satellite, km
            sun_eci_position (``ndarray``): 3x1 ECI position vector of the Sun, km

        Returns:
            `ndarray`: 3x1 ECI acceleration vector due to SRP, km/s^2
        """
        # Vector from satellite to the Sun
        position = sun_eci_position - sat_position
        # SRP acceleration in m/s^2, Montenbruck Eq. 3.75, modified
        a_srp = (
            -const.SOLAR_PRESSURE
            * self.sat_ratio
            * (const.AU2KM / norm(position)) ** 2
            * position
            / norm(position)
        )

        # Multiply SRP acceleration by the percentage of the Sun that is visible, convert to km/s^2
        return a_srp * calculateSunVizFraction(sat_position, sun_eci_position) / 1000.0


def _getRotationMatrix(julian_date: JulianDate, reduction: ReductionParams) -> ndarray:
    """Determine the current ECEF -> ECI rotation matrix.

    References:
        :cite:t:`vallado_2013_astro`, Section 3.7, Eqn 3-57

    Args:
        julian_date (:class:`.JulianDate`): Julian date of the current rotation
        reduction (:class:`.ReductionParameters`): FK5 reductions parameters

    Returns:
        ``ndarray``: 3x3 rotation matrix
    """
    # Convert year and epoch to mdhms form. Time always in UTC
    year, month, day, hours, minutes, seconds = julian_date.calendar_date
    elapsed_days = dayOfYear(year, month, day, hours, minutes, seconds + reduction.dut1) - 1
    greenwich_apparent_sidereal_time = greenwichApparentTime(
        year,
        elapsed_days,
        reduction.eq_equinox,
    )
    return multi_dot(
        [reduction.rot_pn, rot3(-1.0 * greenwich_apparent_sidereal_time), reduction.rot_w],
    )


def _getThirdBodyAcceleration(sat_position: ndarray, third_body_position: ndarray) -> ndarray:
    """Determine the acceleration of a satellite due to a third body.

    Follows Vallado section 8.6.3 equations (8-35) to compute the un-scaled acceleration (the LHS of 8-35).
    Once the un-scaled acceleration is known, it is used to calculate the third-body acceleration from the
    third-body equation (8-34).

    References:
        :cite:t:`vallado_2013_astro`, Section 8.6.3, Eqn 8-34 & 8-35

    Args:
        sat_position (``ndarray``): 3x1 ECI position vector of the satellite, km
        third_body_position (``ndarray``): 3x1 ECI position vector of the third body object, km

    Returns:
        ``ndarray``: 3x1 un-scaled ECI acceleration term due to the third body object, 1/km^2
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
    denominator = (r_e_sat_norm**2 + 2 * vdot(r_e_sat, r_sat_3)) * (
        r_e_3_norm**2 + r_e_3_norm * r_sat_3_norm + r_sat_3_norm**2
    )
    q_3 = denominator / (r_e_3_norm**3 * r_sat_3_norm**3 * (r_e_3_norm + r_sat_3_norm))

    # Compile the un-scaled acceleration
    return r_sat_3 * q_3 - (r_e_sat / (r_e_3_norm**3))


def calcSatRatio(visual_cross_section: float, mass: float, reflectivity: float) -> float:
    r"""Calculate RSO specific value needed for SRP.

    .. math::

        (1.0 + reflectivity) * (\frac{vcs}{mass})

    References:
        :cite:t:`montenbruck_2012_orbits`, Eqn 3.75 - 3.76, Table 3.5

    Args:
            visual_cross_section (``float, int``): constant visual cross-section of the agent (m^2)
            mass (``float, int``): constant mass of the agent (kg)
            reflectivity (``float``): constant reflectivity of the agent (unit-less)

    Returns:
        ``float``: Satellite Ratio of reflectivity to Area / Mass (m^2/kg)
    """
    # Radiation Pressure Coefficient (1 + epsilon) (Montenbruck, Eq. 3.76)
    c_r = 1.0 + reflectivity

    # combine into single variable for simpler code
    return c_r * (visual_cross_section / mass)


def thirdBodyFactory(configuration: list[str]) -> dict:
    """Create third body perturbations based on a config.

    Args:
        configuration (``list``): ``str`` names of third bodies to include

    Returns:
        ``dict``: third body position function multi-dispatch dict
    """
    third_bodies = {}
    for body in configuration:
        if body.lower() == "sun":
            third_bodies[Sun] = "sun"
        elif body.lower() == "moon":
            third_bodies[Moon] = "moon"
        elif body.lower() == "jupiter":
            third_bodies[Jupiter] = "jupiter"
        elif body.lower() == "saturn":
            third_bodies[Saturn] = "saturn"
        elif body.lower() == "venus":
            third_bodies[Venus] = "venus"
        else:
            raise ValueError(f"Incorrect option for 'third_bodies' in config: {body}")

    return third_bodies


def _getGeneralRelativityAcceleration(r_eci: ndarray, v_eci: ndarray) -> ndarray:
    """Calculate the acceleration on the spacecraft due to general relativity.

    References:
        :cite:t:`montenbruck_2012_orbits`, Section 3.7.3, Eqn 3.146, Pg 111

    Args:
        r_eci (``ndarray``): 3x1 ECI position vector of the satellite, km
        v_eci (``ndarray``): 3x1 ECI velocity vector of the satellite, km/s

    Returns:
        ``ndarray``: 3X1 ECI acceleration vector due to general relativity, km/s^2
    """
    r_norm, v_norm = norm(r_eci), norm(v_eci)
    e_r, e_v = r_eci / r_norm, v_eci / v_norm
    # Earth Gravitational constant (km^3/sec^2)
    mu = Earth.mu
    # speed of light squared (km/s)^2
    c_sq = (const.SPEED_OF_LIGHT / 1000) ** 2
    # Intermediate term
    tmp = v_norm**2 / c_sq
    return (mu / r_norm**2) * (
        ((4 * mu) / (c_sq * r_norm) - tmp) * e_r + (4 * tmp) * (vdot(e_r, e_v) * e_v)
    )


def _getGeneralRelativityAccelerationIERS(
    r_eci: ndarray[float, float, float],
    v_eci: ndarray[float, float, float],
    sun_eci: ndarray[float, float, float],
    beta: float = 1.0,
    gamma: float = 1.0,
) -> ndarray:
    """Calculate the relativistic acceleration term of an Earth orbiting satellite.

    This is the method cited by STK and is derived from the IERS equations.

    References:
        :cite:t:`mccarthy_2004_iers`, Eqn 1, Pg 106

    Args:
        r_eci (``ndarray``): 3x1 ECI position vector of the satellite, km
        v_eci (``ndarray``): 3x1 ECI velocity vector of the satellite, km/s
        sun_eci (``ndarray``): 6x1 ECI state vector of the Sun (center), relative to Earth, km; km/s
        beta (``float``, optional): PPN parameter for General Relativity. Defaults to 1.0.
        gamma (``float``, optional): PPN parameter for General Relativity. Defaults to 1.0.

    Returns:
        ``ndarray``: 3x1 ECI acceleration vector due to general relativity, km/s^2
    """
    r_norm = norm(r_eci)
    # Earth & Sun Gravitational constants (km^3/sec^2)
    gme, gms = Earth.mu, Sun.mu
    # Earth's angular momentum per unit mass (km^2/s)
    j_e: ndarray[float, float, float] = array([0.0, 0.0, 980])
    # speed of light squared (km/s)^2
    c_sq = (const.SPEED_OF_LIGHT / 1000) ** 2
    # Intermediate terms
    tmp1 = gme / r_norm
    tmp2 = tmp1 / (c_sq * r_norm**2)
    line_1 = tmp2 * (
        (2 * (beta + gamma) * tmp1 - gamma * vdot(v_eci, v_eci)) * r_eci
        + 2 * (1 + gamma) * vdot(r_eci, v_eci) * v_eci
    )
    line_2 = (
        (1 + gamma)
        * tmp2
        * ((3 / r_norm**2) * cross(r_eci, v_eci) * vdot(r_eci, j_e) + cross(v_eci, j_e))
    )
    line_3 = (1 + 2 * gamma) * cross(
        sun_eci[3:],
        cross((-gms * sun_eci[:3]) / (c_sq * norm(sun_eci[:3]) ** 3), v_eci),
    )
    return line_1 + line_2 + line_3
