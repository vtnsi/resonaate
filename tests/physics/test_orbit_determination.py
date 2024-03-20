"""Test orbit utility functions."""

# Standard Library Imports
# Third Party Imports
import pytest
from numpy import allclose, array

# RESONAATE Imports
from resonaate.physics.orbit_determination.lambert import (
    determineTransferDirection,
    lambertBattin,
    lambertGauss,
    lambertUniversal,
)


@pytest.fixture(name="vallado_inputs")
def getValladoInputs():
    """Return a list of inputs for testing Vallado's IOD examples.

    References:
        :cite:t:`vallado_2013_astro`, Section 7.6, Example 7-5, pg 497
    """
    return [
        array([15945.34, 0.0, 0.0]),
        array([12214.83899, 10249.46731, 0.0]),
        76.0 * 60,
        1,
    ]


def testLambertBattin(vallado_inputs):
    """Test Lambert Battin IOD example."""
    battin_v0 = array([2.058913, 2.915965, 0.0])
    battin_v = array([-3.451565, 0.910301, 0.0])
    initial_velocity, final_velocity = lambertBattin(
        vallado_inputs[0],
        vallado_inputs[1],
        vallado_inputs[2],
        vallado_inputs[3],
    )
    assert allclose(initial_velocity, battin_v0)
    assert allclose(final_velocity, battin_v, rtol=1e-4)


def testLambertBattinSmallDeltaNu(vallado_inputs):
    R"""Test Lambert Battin but delta_nu < PI."""
    initial_velocity, final_velocity = lambertBattin(
        vallado_inputs[0] * -1,
        vallado_inputs[1],
        vallado_inputs[2],
        vallado_inputs[3] * -1,
    )
    assert initial_velocity is not None
    assert final_velocity is not None


def testLambertBattinHyperbolic(vallado_inputs):
    """Test Lambert Battin but sma < 0.0."""
    initial_velocity, final_velocity = lambertBattin(
        vallado_inputs[0],
        vallado_inputs[1],
        vallado_inputs[2],
        vallado_inputs[3],
        mu=1,
    )
    assert initial_velocity is not None
    assert final_velocity is not None


@pytest.mark.filterwarnings("ignore: invalid value encountered in double_scalars")
def testLambertBattinParabolic(vallado_inputs):
    """Test Lambert Battin but sma == 0.0."""
    # [NOTE]: warning filtered b/c shortcut of SMA=0.0 to get parabolic case.
    with pytest.raises(NotImplementedError, match="Parabolic case is not implemented"):
        _, _ = lambertBattin(
            vallado_inputs[0],
            vallado_inputs[1],
            vallado_inputs[2],
            vallado_inputs[3],
            mu=0.0,
        )


def testLambertBattinBadTime(vallado_inputs):
    """Test Lambert Battin but delta_time <= 0.0."""
    with pytest.raises(ValueError, match="delta_time must be positive"):
        _, _ = lambertBattin(vallado_inputs[0], vallado_inputs[1], 0.0, vallado_inputs[3])

    with pytest.raises(ValueError, match="delta_time must be positive"):
        _, _ = lambertBattin(vallado_inputs[0], vallado_inputs[1], -1, vallado_inputs[3])


def testLambertUniversal(vallado_inputs):
    """Test Lambert Universal Variables IOD example."""
    universal_v0 = array([2.058913, 2.915965, 0.0])
    universal_v = array([-3.451565, 0.910315, 0.0])
    initial_velocity, final_velocity = lambertUniversal(
        vallado_inputs[0],
        vallado_inputs[1],
        vallado_inputs[2],
        vallado_inputs[3],
    )
    assert allclose(initial_velocity, universal_v0)
    assert allclose(final_velocity, universal_v)


def testLambertUniversalPoliastro():
    """Test Lambert Universal Variable IOD example.

    Info:
        example info source:
        https://github.com/poliastro/poliastro/blob/main/src/poliastro/core/iod.py
    """
    poliastro_velocity_1_result = array([-5.99249503, 1.92536671, 3.24563805])
    poliastro_velocity_2_result = array([-3.31245851, -4.19661901, -0.38528906])
    initial_state = array([5000, 10000, 2100])
    current_state = array([-14600, 2500, 7000])
    delta_time = 3600  # seconds
    transfer_method = 1
    initial_velocity, final_velocity = lambertUniversal(
        initial_state,
        current_state,
        delta_time,
        transfer_method,
    )
    assert allclose(initial_velocity, poliastro_velocity_1_result)
    assert allclose(final_velocity, poliastro_velocity_2_result)


def testLambertUniversalBadTime(vallado_inputs):
    """Test Lambert Universal but delta_time <= 0.0."""
    with pytest.raises(ValueError, match="delta_time must be positive"):
        _, _ = lambertUniversal(vallado_inputs[0], vallado_inputs[1], 0.0, vallado_inputs[3])

    with pytest.raises(ValueError, match="delta_time must be positive"):
        _, _ = lambertUniversal(vallado_inputs[0], vallado_inputs[1], -1, vallado_inputs[3])


def testLambertUniversalBadAValue(vallado_inputs):
    """Test Lambert Universal but a == 0.0."""
    with pytest.raises(ValueError, match="Singularity occurred, cannot use Universal Lambert"):
        _, _ = lambertUniversal(
            vallado_inputs[0],
            vallado_inputs[1],
            vallado_inputs[2],
            0.0,
        )


def testDetermineTransferDirection():
    """Test determineTransferDirection()."""
    position_vector = array([7000, 0, 0])
    dn1 = determineTransferDirection(position_vector, 10 * 60)
    assert dn1 == 1
    dn2 = determineTransferDirection(position_vector, 5825.036202818729 / 2)
    assert dn2 == 0
    dn3 = determineTransferDirection(position_vector, 180 * 60)
    assert dn3 == -1


def testLambertGauss(vallado_inputs):
    """Test Lambert Gauss IOD example."""
    gauss_v0 = array([2.058913, 2.915965, 0.0])
    gauss_v = array([-3.451565, 0.910315, 0.0])
    initial_velocity, final_velocity = lambertGauss(
        vallado_inputs[0],
        vallado_inputs[1],
        vallado_inputs[2],
        vallado_inputs[3],
    )
    assert allclose(initial_velocity, gauss_v0)
    assert allclose(final_velocity, gauss_v)
