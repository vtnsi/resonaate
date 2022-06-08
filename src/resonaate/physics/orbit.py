# Standard Library Imports
# Third Party Imports
from numpy import asarray, sqrt, concatenate, vdot, arccos, sin, cos
from numpy import inf, matmul, cosh, sinh, finfo, float64
from scipy.linalg import norm
# RESONAATE Imports
from .bodies import Earth
from ..physics import constants as const
from ..physics.math import safeArccos, rot1, rot3, cross


class Orbit:
    """Orbit class defining conversions and behavior of orbits.

    The Orbit Class defines data objects that calculate and store a satellite's orbit, based on
    Classical Orbital Elements. The Orbit Class is also responsible for the conversion between
    orbital elements and state vectors.
    """

    # Smallest representable positive number such that `1.0 + eps != 1.0`
    eps = finfo(float64).eps

    ## [TODO] We can probably change this to use kwargs in the __init__ method?
    def __init__(self, perigee_altitude, ecc, incl, *args):
        """Construct an `Orbit` object from given parameters.

        Inputs(-->)/Outputs(<--):
        -->  perigee_altitude:    Spacecraft's altitude above the Earth's mean equatorial radius at perigee (kilometers)
        -->  ecc:       Orbit's eccentricity  (unitless)
        -->  varargin:  Variable number of inputs based on the type of orbit (all radians)
        """
        perigee_radius = Earth.radius + perigee_altitude
        self.semimajor_axis = perigee_radius / (1 - ecc)
        self.eccentricity = ecc
        self.inclination = const.DEG2RAD * incl

        if len(args) == 3:  # Inclined, Eccentric Orbits
            self.right_ascension = const.DEG2RAD * args[0]
            self.argument_periapsis = const.DEG2RAD * args[1]
            self.true_anomaly = const.DEG2RAD * args[2]

        elif len(args) == 2:
            if (ecc > self.eps) and (abs(incl) <= self.eps):   # Equatorial, Eccentric Orbits
                self.true_long_periapsis = const.DEG2RAD * args[0]
                self.true_anomaly = const.DEG2RAD * args[1]

            elif (ecc <= self.eps) and (abs(incl) > self.eps):   # Inclined, Circular Orbits
                self.right_ascension = const.DEG2RAD * args[0]
                self.argument_latitude = const.DEG2RAD * args[1]

            else:
                raise ValueError("Inputted Orbital Elements do not describe a valid orbit.")

        elif len(args) == 1:  # Equatorial, Circular Orbits
            self.true_longitude = const.DEG2RAD * args[0]

        else:
            raise ValueError("Incorrect number of input variables.")

        self.semilatus_rectum = self.semimajor_axis * (1 - ecc**2)
        self.period = 2 * const.PI * sqrt(self.semimajor_axis**3 / Earth.mu)
        self.mean_motion = 2 * const.PI / self.period

        self.ecc_anomaly = None
        self.mean_anomaly = None

    @classmethod
    def buildFromCOEConfig(cls, config):
        """Construct an `Orbit` object from a configuration dictionary.

        @param config \b dict -- dictionary of arguments that define a valid orbit
        """
        base_args = all([arg in config.keys() for arg in ("orbitAlt", "ecc", "incl")])

        if base_args and all([arg in config.keys() for arg in ("right_ascension", "argPeriapsis", "true_anomaly")]):
            return cls(config["orbitAlt"], config["ecc"], config["incl"],
                       config["right_ascension"], config["argPeriapsis"], config["true_anomaly"])

        if base_args and all([arg in config.keys() for arg in ("true_long_periapsis", "true_anomaly")]):
            return cls(config["orbitAlt"], config["ecc"], config["incl"],
                       config["true_long_periapsis"], config["true_anomaly"])

        if base_args and all([arg in config.keys() for arg in ("right_ascension", "argLatitude")]):
            return cls(config["orbitAlt"], config["ecc"], config["incl"],
                       config["right_ascension"], config["argLatitude"])

        if base_args and all([arg in config.keys() for arg in "true_longitude"]):
            return cls(config["orbitAlt"], config["ecc"], config["incl"], config["true_longitude"])

        msg = "The classical orbital element set"
        raise ValueError("{0} '{1}' does not describe a valid orbit.".format(msg, config.keys()))

    def coe2rv(self):
        """Calculate the spacecraft's 6x1 ECI state vector from the stored COE.

        Inputs(-->)/Outputs(<--):
        <--  x_val:     6x1 ECI state vector (km km/sec)
        """
        # Calculations for a circular equatorial orbit
        if getattr(self, 'true_longitude', None) is not None:
            # True anomaly replacement
            cos_nu = cos(self.true_longitude)
            sin_nu = sin(self.true_longitude)
            # Undefined
            arg_p = 0
            raan = 0

        #   Calculations for a circular inclined orbit
        elif getattr(self, 'argument_latitude', None) is not None:
            # True anomaly replacement
            cos_nu = cos(self.argument_latitude)
            sin_nu = sin(self.argument_latitude)
            # Undefined
            arg_p = 0
            # Retrieve defined OE's
            raan = self.right_ascension

        #   Calculations for an eccentric equatorial orbit
        elif getattr(self, 'true_long_periapsis', None) is not None:
            # True anomaly replacement
            cos_nu = cos(self.true_anomaly)
            sin_nu = sin(self.true_anomaly)
            # Retrieve defined OE's
            arg_p = self.true_long_periapsis
            # Undefined
            raan = 0

        #   Calculations for an eccentric inclined orbit
        else:
            # True anomaly
            cos_nu = cos(self.true_anomaly)
            sin_nu = sin(self.true_anomaly)
            # Retrieve defined OE's
            arg_p = self.argument_periapsis
            raan = self.right_ascension

        pqw_to_ijk = matmul(matmul(rot3(-1 * raan), rot1(-1 * self.inclination)), rot3(-1 * arg_p))

        #   Calculations for position and velocity vectors in Perifocal (PQW) frame
        r_pqw = self.semilatus_rectum / (1 + self.eccentricity * cos_nu) * asarray([cos_nu, sin_nu, 0])
        v_pqw = sqrt(Earth.mu / self.semilatus_rectum) * asarray([-sin_nu, self.eccentricity + cos_nu, 0])

        #   Conversion of PQW position and velocity vectors to ECI state vector
        x_val = concatenate([matmul(pqw_to_ijk, r_pqw), matmul(pqw_to_ijk, v_pqw)], axis=0)

        return x_val.reshape(6)

    @classmethod  # noqa: C901
    def rv2coe(cls, x_val):
        """Construct an `Orbit` object based on a 6x1 ECI state vector.

        Inputs(-->)/Outputs(<--):
        -->  x_val:    6x1 ECI state vector (km km/sec)
        <--  new_orbit:  1x1 Orbit object
        """
        # Instantiate an empty orbit object.
        new_orbit = cls(0, 0, 0, 0)

        #   Calculate position and velocity vector
        if x_val.size == (6, 1):
            r_vector = concatenate(x_val[0:3].T)
            v_vector = concatenate(x_val[3:6].T)
        elif x_val.size == 6:
            r_vector = x_val[0:3]
            v_vector = x_val[3:6]

        # Vector magnitudes
        r_norm = norm(r_vector)
        v_norm = norm(v_vector)

        #   Calculate specific energy
        energy = v_norm**2 / 2 - Earth.mu / r_norm

        #   Calculate angular momentum and nodal vector
        h_vector = cross(r_vector, v_vector)
        h_norm = norm(h_vector)
        node_vector = cross(asarray([0, 0, 1]), h_vector)
        node_norm = norm(node_vector)

        #   Calculate eccentricity vector and magnitude
        e_vector = ((v_norm**2 - Earth.mu / r_norm) * r_vector - vdot(r_vector, v_vector) * v_vector) / Earth.mu
        ecc = norm(e_vector)

        #   Calculate Semimajor Axis and Semilatus Rectum based on eccentricity
        if ecc != 1.0:
            a_val = -Earth.mu / (2 * energy)
            p_val = a_val * (1 - ecc**2)
        else:
            a_val = inf
            p_val = h_norm**2 / Earth.mu

        #   Calculate Inclination
        incl = arccos(h_vector[2] / h_norm)

        #   Set Orbit object properties
        new_orbit.semimajor_axis = a_val
        new_orbit.semilatus_rectum = p_val
        new_orbit.eccentricity = ecc
        new_orbit.inclination = incl
        new_orbit.period = 2 * const.PI * sqrt((new_orbit.semimajor_axis**3) / Earth.mu)
        new_orbit.mean_motion = 2 * const.PI / new_orbit.period
        new_orbit.right_ascension = None
        new_orbit.argument_periapsis = None
        new_orbit.true_anomaly = None
        new_orbit.true_long_periapsis = None
        new_orbit.argument_latitude = None
        new_orbit.true_longitude = None
        #    New parameters based on new r_norm value
        new_orbit.ecc_anomaly = safeArccos((1 - r_norm / new_orbit.semimajor_axis) / new_orbit.eccentricity)
        new_orbit.mean_anomaly = new_orbit.ecc_anomaly - ecc * sin(new_orbit.ecc_anomaly)

        if ecc >= cls.eps and abs(incl) >= cls.eps:      # Inclined, Eccentric Orbits
            #   Calculate Right Ascension of the Ascending Node
            raan = arccos(node_vector[0] / node_norm)
            if node_vector[1] < 0:
                raan = 2 * const.PI - raan

            #   Calculate Argument of Periapsis
            argp = arccos(vdot(node_vector, e_vector) / (node_norm * ecc))
            if e_vector[2] < 0:
                argp = 2 * const.PI - argp

            #   Calculate True Anomaly
            tanom = safeArccos(vdot(e_vector, r_vector) / (ecc * r_norm))
            if vdot(r_vector, v_vector) < 0:
                tanom = 2 * const.PI - tanom

            new_orbit.right_ascension = raan
            new_orbit.argument_periapsis = argp
            new_orbit.true_anomaly = tanom

        elif ecc >= cls.eps and abs(incl) < cls.eps:       # Equatorial, Eccentric Orbits
            #   Calculate True Longitude of Periapsis
            truep = arccos(e_vector[0] / ecc)
            if e_vector[1] < cls.eps:
                truep = 2 * const.PI - truep

            #   Calculate True Anomaly
            tanom = arccos(vdot(e_vector, r_vector) / (ecc * r_norm))
            if vdot(r_vector, v_vector) < 0:
                tanom = 2 * const.PI - tanom

            new_orbit.true_anomaly = tanom
            new_orbit.true_long_periapsis = truep

        elif ecc < cls.eps and abs(incl) >= cls.eps:        # Inclined, Circular Orbits
            #   Calculate Right Ascension of the Ascending Node
            raan = arccos(node_vector[0] / node_norm)
            if node_vector[1] < 0:
                raan = 2 * const.PI - raan

            #   Calculate Argument of Latitude
            arglat = arccos(vdot(node_vector, r_vector) / (node_norm * r_norm))
            if r_vector[2] < 0:
                arglat = 2 * const.PI - arglat

            new_orbit.right_ascension = raan
            new_orbit.argument_latitude = arglat

        else:                                    # Circular, Equatorial Orbits
            #   Calculate True Longitude
            truelong = arccos(r_vector[0] / r_norm)
            if r_vector[1] < 0:
                truelong = 2 * const.PI - truelong

            new_orbit.true_longitude = truelong

        return new_orbit


def universalC2C3(psi):
    """."""
    c_val = []
    if psi > 1e-6:
        c2_val = (1 - cos(sqrt(psi))) / psi
        c3_val = (sqrt(psi) - sin(sqrt(psi))) / sqrt(psi**3)
        c_val.insert(0, c2_val)
        c_val.insert(1, c3_val)
    elif psi < -1e-6:
        c2_val = (1 - cosh(sqrt(-psi))) / psi
        c3_val = (sinh(sqrt(psi)) - sqrt(-psi)) / sqrt(-psi**3)
        c_val.insert(0, c2_val)
        c_val.insert(0, c3_val)
    else:
        c2_val = 0.5
        c3_val = 1 / 6.
        c_val.insert(0, c2_val)
        c_val.insert(0, c3_val)
    return c_val
