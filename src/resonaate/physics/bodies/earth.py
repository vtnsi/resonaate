# Standard Library Imports
from csv import reader
from pkg_resources import resource_filename
# Third Party Imports
from numpy import asarray, zeros, sqrt
from scipy.linalg import norm
from scipy.special import factorial
# RESONAATE Imports


def _loadGeopotentialCoefficients(earth_model_file):
    """Read the gravity model file & save the geopotential coefficients."""
    gravity_model_file = resource_filename('resonaate', 'physics/data/{0}'.format(earth_model_file))
    with open(gravity_model_file, 'r') as csv_file:
        cos_terms = zeros((181, 181))
        sin_terms = zeros((181, 181))
        for row in reader(csv_file, delimiter=' ', skipinitialspace=True):
            degree, order = int(row[0]), int(row[1])
            cos_terms[degree, order] = float(row[2])
            sin_terms[degree, order] = float(row[3])

    return cos_terms, sin_terms


class Earth:
    """The central gravitational body for Resonaate with defined constants.

    See Also:
     Vallado Ed. 4, Appendix D.1, Table D-1.
    """

    # Standard Earth constants. [TODO]: Source these from a singular place/model (GGM03S?)
    mu = 398600.4415
    """float: gravitational parameter, (km^3/sec^2)."""
    radius = 6378.1363
    """float: mean equatorial radius (km)."""
    mass = 5.9742e24
    """float: planet's mass, (km)."""
    spin_rate = 7.292115146706979e-5
    """float: rotation rate about the *K*-axis (ECEF), (rad/sec)."""
    eccentricity = 0.081819221456
    """float: equatorial bulge, (untiless)."""
    atmosphere = 100.
    """float: assumed height of the atmosphere, (km)."""

    # Geopotential coefficients for non-spherical gravity model (up to 181x181)
    c_nm, s_nm = None, None

    # EGM-08 Zonal coefficients (normalized). Vallado Ed. 4, Appendix D.1, Table D-1. Dimensionless
    #   [NOTE]: J_i = -C_i = Cbar_i,0 / PI_i,o
    J2 = 1.08262617385222e-3
    """float: second-order zonal coefficient, (unitless)."""
    J3 = -2.53241051856772e-6
    """float: third-order zonal coefficient, (unitless)."""
    J4 = -1.61989759991697e-6
    """float: fourth-order zonal coefficient, (unitless)."""

    def __init__(self, earth_model):
        """Load geopotential data into Earth model."""
        self.c_nm, self.s_nm = _loadGeopotentialCoefficients(earth_model)

    @staticmethod
    def getNonSphericalHarmonics(ecef_position, degree, order):
        """Compute the harmonic terms for a given position & gravity field.

            The equations follow the recurrence relations defined in "Satellite Orbits" by Montenbruck (3.29 - 3.31).
            In general, the gravity model order must be less than or equal to the gravity model degree.

        Args:
            ecef_position (``numpy.ndarray``): ITRF/ECEF for which to calculate harmonic terms [km]
            degree (int): maximum degree (N) of the gravity model
            order (int): maximum order (M) of the gravity model

        Returns:
            ``numpy.ndarray``: matrix of recursive cosine harmonic terms (N+1 x M+1)
            ``numpy.ndarray``: matrix of recursive sine harmonic terms (N+1 x M+1)
        """
        # Temporary variables for convenience
        norm_r = norm(ecef_position)
        rho = Earth.radius / norm_r
        rho_sq = rho**2
        # Normalize the ITRF/ECEF coordinates
        [x_bar, y_bar, z_bar] = ecef_position * rho / norm_r

        # Initialize & pre-compute the harmonics terms
        v_mat = zeros((degree + 1, order + 1))
        w_mat = zeros((degree + 1, order + 1))

        v_mat[0, 0] = rho
        v_mat[1, 0] = z_bar * v_mat[0, 0]
        v_mat[1, 1] = x_bar * v_mat[0, 0]
        w_mat[1, 1] = y_bar * v_mat[0, 0]

        # Harmonic term recurrence relations defined in "Satellite Orbits" by Montenbruck (3.29 - 3.31)
        for mmm in range(order + 1):
            for nnn in range(2, degree + 1):
                # Skip terms above the diagonal
                if mmm > nnn:  # pylint: disable=no-else-continue
                    continue
                # Diagonal terms
                elif mmm == nnn:
                    v_mat[mmm, mmm] = (2 * mmm - 1) * (x_bar * v_mat[mmm - 1, mmm - 1]
                                                       - y_bar * w_mat[mmm - 1, mmm - 1])
                    w_mat[mmm, mmm] = (2 * mmm - 1) * (x_bar * w_mat[mmm - 1, mmm - 1]
                                                       + y_bar * v_mat[mmm - 1, mmm - 1])
                # Off-diagonal terms (m < n)
                else:
                    v_mat[nnn, mmm] = ((2 * nnn - 1) * z_bar * v_mat[nnn - 1, mmm]
                                       - (nnn + mmm - 1) * rho_sq * v_mat[nnn - 2, mmm]) / (nnn - mmm)
                    if mmm != 0:
                        w_mat[nnn, mmm] = ((2 * nnn - 1) * z_bar * w_mat[nnn - 1, mmm]
                                           - (nnn + mmm - 1) * rho_sq * w_mat[nnn - 2, mmm]) / (nnn - mmm)

        return v_mat, w_mat

    def nonSphericalGeopotential(self, ecef_position, max_degree, max_order):
        """Compute the non-spherical geopotential acceleration.

            The equations are defined in "Satellite Orbits" by Montenbruck (3.32 - 3.33).
            In general, the gravity model order must be less than or equal to the gravity model degree.

        Args:
            ecef_position (``numpy.ndarray``): ITRF/ECEF for which to calculate the acceleration terms [km]
            max_degree (int): maximum degree (N) of the gravity model
            max_order (int): maximum order (M) of the gravity model

        Returns:
            ``numpy.ndarray``: vector of geopotential acceleration terms in ITRF/ECEF coordinates
        """
        # We require one degree & order higher harmonic terms due to the partial acceleration equations
        v_mat, w_mat = self.getNonSphericalHarmonics(ecef_position, max_degree + 1, max_order + 1)
        acceleration = zeros((3, ))
        for nnn in range(2, max_degree + 1):
            for mmm in range(max_order + 1):
                # Terms above diagonal aren't used/don't exist
                if mmm > nnn:
                    continue
                # Zonal partial acceleration terms (simplified x/y/z equations)
                if mmm == 0:
                    scale = sqrt(1 / (2 * nnn + 1))
                    terms = asarray(
                        [
                            -self.c_nm[nnn, 0] * v_mat[nnn + 1, 1],
                            -self.c_nm[nnn, 0] * w_mat[nnn + 1, 1],
                            -(nnn + 1) * self.c_nm[nnn, 0] * v_mat[nnn + 1, 0]
                        ]
                    )
                # Tesseral & sectoral partial accelerations terms
                else:
                    fact_term = (nnn - mmm + 1) * (nnn - mmm + 2)
                    scale = sqrt(factorial(nnn + mmm) / (factorial(nnn - mmm) * 2 * (2 * nnn + 1)))
                    x_term = 0.5 * (
                        -self.c_nm[nnn, mmm] * v_mat[nnn + 1, mmm + 1]
                        - self.s_nm[nnn, mmm] * w_mat[nnn + 1, mmm + 1]
                        + fact_term * (
                            self.c_nm[nnn, mmm] * v_mat[nnn + 1, mmm - 1]
                            + self.s_nm[nnn, mmm] * w_mat[nnn + 1, mmm - 1]
                        )
                    )
                    y_term = 0.5 * (
                        -self.c_nm[nnn, mmm] * w_mat[nnn + 1, mmm + 1]
                        + self.s_nm[nnn, mmm] * v_mat[nnn + 1, mmm + 1]
                        + fact_term * (
                            -self.c_nm[nnn, mmm] * w_mat[nnn + 1, mmm - 1]
                            + self.s_nm[nnn, mmm] * v_mat[nnn + 1, mmm - 1]
                        )
                    )
                    z_term = (nnn - mmm + 1) * (
                        -self.c_nm[nnn, mmm] * v_mat[nnn + 1, mmm]
                        - self.s_nm[nnn, mmm] * w_mat[nnn + 1, mmm]
                    )
                    terms = asarray([x_term, y_term, z_term])

                # Scale terms and increment non-spherical acceleration
                acceleration += terms / scale

        return acceleration * self.mu / (self.radius ** 2)
