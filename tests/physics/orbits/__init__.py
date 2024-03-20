from __future__ import annotations

# Standard Library Imports
from typing import TYPE_CHECKING

# Third Party Imports
from numpy import array, deg2rad, finfo

# RESONAATE Imports
from resonaate.physics.bodies import Earth
from resonaate.physics.orbits import ECCENTRICITY_LIMIT, INCLINATION_LIMIT

# Type Checking Imports
if TYPE_CHECKING:
    # Third Party Imports
    from numpy import ndarray

# Valid and invalid Inc/Ecc for testing edge cases

INCLINATIONS: tuple[float] = (
    0.0,
    finfo(float).eps,
    INCLINATION_LIMIT,
    INCLINATION_LIMIT + finfo(float).eps,
    deg2rad(1.0),
    deg2rad(30.0),
    deg2rad(90.0),
    deg2rad(130.0),
    deg2rad(179.99),
    deg2rad(180) - (INCLINATION_LIMIT + finfo(float).eps),
    deg2rad(180) - INCLINATION_LIMIT,
    deg2rad(180) - finfo(float).eps,
    deg2rad(180),
    deg2rad(181),
    deg2rad(-5),
)
INCLINED: tuple[bool] = (
    False,
    False,
    True,
    True,
    True,
    True,
    True,
    True,
    True,
    True,
    True,
    False,
    False,
    None,
    None,
)


ECCENTRICITIES: tuple[float] = (
    0.0,
    finfo(float).eps,
    ECCENTRICITY_LIMIT,
    ECCENTRICITY_LIMIT + finfo(float).eps,
    0.01,
    0.1,
    0.5,
    0.9,
    0.99,
    1.0 - (ECCENTRICITY_LIMIT + finfo(float).eps),
    1.0 - ECCENTRICITY_LIMIT,
    1.0 - finfo(float).eps,
    1.0,
    1.1,
    -0.1,
)
ECCENTRIC: tuple[bool] = (
    False,
    False,
    True,
    True,
    True,
    True,
    True,
    True,
    True,
    True,
    True,
    None,
    None,
    None,
    None,
)


# All valid inputs, for parametrically testing functions/classes

# TEMP VARS
LEO: float = 7078
GEO: float = 35785 + Earth.radius

# COEs
SMA: ndarray = array(
    [LEO, GEO, LEO, LEO, LEO, LEO, LEO, LEO, GEO, LEO, LEO, LEO, LEO, GEO],
    dtype=float,
)
ECC: ndarray = array(
    [0, 0, 0, 0.0001, 0.0001, 0.001, 0.01, 0.1, 0, 0.0001, 0.001, 0.01, 0.1, 0.0001],
    dtype=float,
)
INC: ndarray = deg2rad([0, 0, 10, 0.1, 0, 1, 10, 100, 10, 0, 1, 0.1, 1, 100])
RAAN: ndarray = deg2rad([0, 0, 12, 55, 0, 324, 127, 61, 12, 0, 55, 324, 127, 10])
ARGP: ndarray = deg2rad([0, 0, 0, 300, 200, 100, 15, 1, 0, 10, 1, 300, 100, 1])
ANOM: ndarray = deg2rad([280, 280, 2, 20, 20, 200, 70, 140, 140, 2, 20, 200, 70, 2])

# EQEs
H: ndarray = array(
    [0.0, 0.0001, 0.001, 0.01, 0.15, 0.2, 0.3, 0.61, 0.3, 0.1, 0.2, 0.11, 0.02, 0.08],
    dtype=float,
)
K: ndarray = array(
    [0.0, 0.0002, 0.001, 0.03, 0.1, 0.25, 0.3, 0.61, 0.5, 0.3, 0.21, 0.1, 0.04, 0.04],
    dtype=float,
)
P: ndarray = array([1, 1, 1, 1, 1, 2, 2, 2, 1, 2, 3, 3, 1, 6], dtype=float)
Q: ndarray = array([1, 2, 3, 4, 2, 2, 3, 4, 3, 3, 3, 4, 6, 1], dtype=float)

# VALLADO AAS RV/COE/EQE Sets
# Example from "Updated Analytical Partials for Covariance Transformations and Optimizations", Vallado
VALLADO_AAS_RV: ndarray = array(
    [-605.7922166, -5870.2295111, 3493.0531990, -1.568254290, -3.702348910, -6.479483950],
)
VALLADO_AAS_COE: tuple[float] = (
    6860.7631,
    0.0010640,
    deg2rad(97.65184),
    deg2rad(79.54701),
    deg2rad(83.86041),
    deg2rad(65.21303),
)
VALLADO_AAS_EQE: tuple[float] = (
    # SMA,         h = a_g    k = a_f    p = chi    q = psi    lambda_M
    6860.7631490,
    0.0000800,
    0.0010610,
    0.8601197,
    0.1586839,
    deg2rad(69.4157838),
)

POS_TEST_CASES: tuple[ndarray] = (
    # Example 2-5 from Vallado Text
    array([6524.834, 6862.875, 6448.296]),
    # Elliptical, inclined tests from Vallado code
    array([1.1372844, -1.0534274, -0.8550194]) * 6378.137,
    array([1.0561942, -0.8950922, -0.0823703]) * 6378.137,
    # Near circular, inclined tests from Vallado code
    array([-0.4222777, 1.0078857, 0.7041832]) * 6378.137,
    array([-0.7309361, -0.6794646, -0.8331183]) * 6378.137,
    # Circular, inclined tests from Vallado code
    array([-2693.34555010128, 6428.43425355863, 4491.37782050409]),
    array([-7079.68834483379, 3167.87718823353, -2931.53867301568]),
    # Elliptical, near equatorial tests from Vallado code
    array([21648.6109280739, -14058.7723188698, -0.0003598029]),
    array([7546.9914487222, 24685.1032834356, -0.0003598029]),
    # Elliptical, equatorial tests from Vallado code
    array([-22739.1086596208, -22739.1086596208, 0.0]),
    # Circular, near equatorial tests from Vallado code
    array([-2547.3697454933, 14446.8517254604, 0.000]),
    array([7334.858850000, -12704.3481945462, 0.000]),
    # Circular, equatorial tests from Vallado code
    array([6199.6905946008, 13295.2793851394, 0.0]),
)
VEL_TEST_CASES: tuple[ndarray] = (
    # Example 2-5 from Vallado Text
    array([4.901327, 5.533756, -1.976341]),
    # Elliptical, inclined tests from Vallado code
    array([0.6510489, 0.4521008, 0.0381088]) * 7.905366149846,
    array([-0.5981066, -0.6293575, 0.1468194]) * 7.905366149846,
    # Near circular, inclined tests from Vallado code
    array([-0.5002738, -0.5415267, 0.4750788]) * 7.905366149846,
    array([-0.6724131, 0.0341802, 0.5620652]) * 7.905366149846,
    # Circular, inclined tests from Vallado code
    array([-3.95484712246016, -4.28096585381370, 3.75567104538731]),
    array([1.77608080328182, 6.23770933190509, 2.45134017949138]),
    # Elliptical, near equatorial tests from Vallado code
    array([2.16378060719980, 3.32694348486311, 0.00000004164788]),
    array([3.79607016047138, -1.15773520476223, 0.00000004164788]),
    # Elliptical, equatorial tests from Vallado code
    array([2.48514004188565, -2.02004112073465, 0.0]),
    # Circular, near equatorial tests from Vallado code
    array([-5.13345156333487, -0.90516601477599, 0.00000090977789]),
    array([-4.51428154312046, -2.60632166411836, 0.00000090977789]),
    # Circular, equatorial tests from Vallado code
    array([-4.72425923942564, 2.20295826245369, 0.0]),
)
