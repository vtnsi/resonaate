from __future__ import annotations

# Standard Library Imports
from datetime import datetime
from typing import TYPE_CHECKING

# Third Party Imports
import pytest
from numpy import allclose
from numpy import any as np_any
from numpy import array, dot
from numpy.linalg import norm

# RESONAATE Imports
from resonaate.common.labels import GeopotentialModel
from resonaate.dynamics.special_perturbations import _getRotationMatrix
from resonaate.physics.bodies import Earth
from resonaate.physics.bodies.gravitational_potential import (
    loadGeopotentialCoefficients,
    nonSphericalAcceleration,
)
from resonaate.physics.time.stardate import datetimeToJulianDate
from resonaate.physics.transforms.methods import eci2ecef
from resonaate.physics.transforms.reductions import ReductionParams

# Type Checking Imports
if TYPE_CHECKING:
    # Third Party Imports
    from numpy import ndarray


TEST_CASES: list[tuple[int, int, ndarray]] = [
    # (degree, order, [truth])
    (2, 0, [-0.023402725520133, 0.178921657872794, -0.158647615812368]),
    (4, 4, [-0.025272814133158, 0.180129562607620, -0.156608150434144]),
    (16, 16, [-0.025220531457556, 0.180512517258954, -0.156448742777998]),
    (48, 48, [-0.025220876219449, 0.180513294718102, -0.156448843984580]),
]
# IERS test cases, no formal reference to where these came from

ITRF_POSITION: ndarray = array([-1033.4793830, 7901.2952754, 6380.3565958])  # km

GRAVITY_MODELS: list[tuple[str, bool]] = [
    # (model, is_valid)
    ("GGM03S.txt", True),
    ("egm96.txt", True),
    ("egm2008.txt", True),
    ("jgm3.txt", True),
    ("jgm1.txt", False),
]


@pytest.mark.parametrize(("degree", "order", "truth"), TEST_CASES)
def testGeoPotentialFunction(degree: int, order: int, truth: ndarray):
    """Test the non-spherical geopotential acceleration function."""
    c_nm, s_nm = loadGeopotentialCoefficients(GeopotentialModel("egm96.txt"))
    accelerations = nonSphericalAcceleration(
        ITRF_POSITION,
        Earth.mu,
        Earth.radius,
        c_nm,
        s_nm,
        degree,
        order,
    )
    assert allclose(accelerations, array(truth) * 1e-5, atol=1e-10, rtol=1e-8)


def testNonsphericalAcceleration():
    """Calculate non-spherical acceleration and compare versus STK values."""
    # STK Scenario using HPOP, 4x4 EGM96 gravity model only.
    _datetime = datetime(2020, 3, 30, 16)
    jd = datetimeToJulianDate(_datetime)
    # Initial state vector
    eci_state = array(
        [
            -1775.038314593,
            5669.031509330,
            3035.224600923,
            -7.108806806,
            -2.822740035,
            1.130313493,
        ],
    )
    # Full acceleration values
    eci_accel = array([2.383405021e-03, -7.611372878e-03, -4.087216625e-03])
    ecef_state = eci2ecef(eci_state, _datetime)
    ecef2eci = _getRotationMatrix(jd, ReductionParams.build(_datetime))

    c_nm, s_nm = loadGeopotentialCoefficients(GeopotentialModel("egm96.txt"))

    # Subtract Keplerian motion acceleration to retrieve nonspherical terms only.
    tb_accel = -1.0 * Earth.mu / (norm(eci_state[:3]) ** 3.0) * eci_state[:3]
    truth_accel = eci_accel - tb_accel

    # Calculate nonspherical acceleration using RESONAATE algorithm
    ns_accel = dot(
        ecef2eci,
        nonSphericalAcceleration(ecef_state[:3], Earth.mu, Earth.radius, c_nm, s_nm, 4, 4),
    )

    assert allclose(ns_accel, truth_accel, atol=1e-10, rtol=1e-8)


@pytest.mark.parametrize(("model", "is_valid"), GRAVITY_MODELS)
def testLoadingGravityModels(model: str, is_valid: bool):
    """Testing loading valid/invalid gravity models."""
    if is_valid:
        c_nm, s_nm = loadGeopotentialCoefficients(GeopotentialModel(model))
        assert np_any(c_nm)
        assert np_any(s_nm)

    else:  # invalid
        with pytest.raises(ValueError, match=f"'{model}' is not a valid GeopotentialModel"):
            loadGeopotentialCoefficients(GeopotentialModel(model))
