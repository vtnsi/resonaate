from __future__ import annotations

# Standard Library Imports
from typing import TYPE_CHECKING

# Third Party Imports
import pytest
from numpy import allclose, array, concatenate, deg2rad
from scipy.linalg import norm

# RESONAATE Imports
from resonaate.physics.orbits.conversions import (
    coe2eci,
    coe2eqe,
    eci2coe,
    eci2eqe,
    eqe2coe,
    eqe2eci,
)

# Local Imports
from . import (
    ANOM,
    ARGP,
    ECC,
    INC,
    POS_TEST_CASES,
    RAAN,
    SMA,
    VALLADO_AAS_COE,
    VALLADO_AAS_EQE,
    VALLADO_AAS_RV,
    VEL_TEST_CASES,
    H,
    K,
    P,
    Q,
)

# Type Checking Imports
if TYPE_CHECKING:
    # Third Party Imports
    from numpy import ndarray

COE_SET: tuple[tuple[float, float, float, float, float, float]] = tuple(
    zip(SMA, ECC, INC, RAAN, ARGP, ANOM),
)
EQE_SET: tuple[tuple[float, float, float, float, float, float]] = tuple(zip(SMA, H, K, P, Q, ANOM))
RV_CASES: tuple[tuple[ndarray, ndarray]] = tuple(zip(POS_TEST_CASES, VEL_TEST_CASES))


@pytest.mark.parametrize(("sma", "ecc", "inc", "raan", "argp", "anom"), COE_SET)
def testCOE(sma: float, ecc: float, inc: float, raan: float, argp: float, anom: float):
    """Test COE conversion functions to make sure they are reversible."""
    orig_coe = [sma, ecc, inc, raan, argp, anom]
    eci = coe2eci(*orig_coe)
    assert allclose(orig_coe, eci2coe(eci), rtol=1e-8, atol=1e-8)

    eqe = coe2eqe(*orig_coe)
    new_coe = eqe2coe(*eqe)
    assert allclose(orig_coe, new_coe, rtol=1e-8, atol=1e-8)


def testCOE2RV():
    """Values from examples in Chapter 2 of Vallado: Examples 2-6."""
    eci = array([6525.368, 6861.532, 6449.119, 4.902279, 5.533140, -1.975710])
    coe = (
        11067.790 / (1 - 0.83285**2),
        0.83285,
        deg2rad(87.87),
        deg2rad(227.89),
        deg2rad(53.38),
        deg2rad(92.335),
    )
    new_eci = coe2eci(*coe)
    assert allclose(new_eci, eci, rtol=1e-4, atol=1e-6)


def testRV2COE():
    """Values from examples in Chapter 2 of Vallado: Examples 2-5."""
    eci = array([6524.834, 6862.875, 6448.296, 4.901327, 5.533756, -1.976341])
    coe = (
        36127.343,
        0.832853,
        deg2rad(87.870),
        deg2rad(227.898),
        deg2rad(53.38),
        deg2rad(92.335),
    )
    new_coe = eci2coe(eci, mu=398600.4418)
    assert allclose(new_coe, coe, rtol=1e-4, atol=1e-6)


@pytest.mark.parametrize(("sma", "h", "k", "p", "q", "anom"), EQE_SET)
def testEQE(sma: float, h: float, k: float, p: float, q: float, anom: float):
    """Test EQE conversion functions to make sure they are reversible."""
    orig_eqe = [sma, h, k, p, q, anom]
    eci = eqe2eci(*orig_eqe)
    assert allclose(orig_eqe, eci2eqe(eci), rtol=1e-8, atol=1e-8)

    coe = eqe2coe(*orig_eqe)
    new_eqe = coe2eqe(*coe)
    assert allclose(orig_eqe, new_eqe, rtol=1e-8, atol=1e-8)


@pytest.mark.parametrize(("pos", "vel"), RV_CASES)
def testRVConversions(pos: ndarray, vel: ndarray):
    """Test converting from ECI to COE/EQE and back using cases from Vallado."""
    orig_eci = concatenate((pos, vel), axis=0)
    coe = eci2coe(orig_eci)
    new_eci_from_coe = coe2eci(*coe)
    diff_eci = orig_eci - new_eci_from_coe
    assert norm(diff_eci[:3]) < 5e-4
    assert norm(diff_eci[3:]) < 1e-7
    # assert False
    eqe = eci2eqe(orig_eci)
    new_eci_from_eqe = eqe2eci(*eqe)
    diff_eqe = orig_eci - new_eci_from_eqe
    assert norm(diff_eqe[:3]) < 1e-4
    assert norm(diff_eqe[3:]) < 5e-8


def testAASVallado():
    """Test converting btwn COE, EQE, ECI comparing to Vallado AAS paper."""
    # COE -> ECI
    new_eci = coe2eci(*VALLADO_AAS_COE)
    assert allclose(new_eci, VALLADO_AAS_RV, rtol=1e-6, atol=1e-8)
    # ECI -> COE
    new_coe = eci2coe(VALLADO_AAS_RV)
    assert allclose(new_coe, VALLADO_AAS_COE, rtol=1e-5, atol=1e-8)
    # COE -> EQE
    new_eqe = coe2eqe(*VALLADO_AAS_COE, retro=True)
    assert allclose(new_eqe, VALLADO_AAS_EQE, rtol=1e-7, atol=1e-7)
    # EQE -> COE
    new_coe = eqe2coe(*VALLADO_AAS_EQE, retro=True)
    assert allclose(new_coe, VALLADO_AAS_COE, rtol=1e-5, atol=1e-4)
    # EQE -> ECI
    new_eci = eqe2eci(*VALLADO_AAS_EQE, retro=True)
    assert allclose(new_eci, VALLADO_AAS_RV, rtol=1e-6, atol=1e-8)
    # ECI -> EQE
    new_eqe = eci2eqe(VALLADO_AAS_RV, retro=True)
    assert allclose(new_eqe, VALLADO_AAS_EQE, rtol=1e-5, atol=1e-5)
