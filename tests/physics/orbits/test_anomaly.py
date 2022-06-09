# pylint: disable=attribute-defined-outside-init, no-self-use
# Standard Library Imports
# Third Party Imports
import pytest
from numpy import cos, deg2rad, isclose, rad2deg, sin
# RESONAATE Imports
try:
    from resonaate.physics.orbits.anomaly import (
        eccAnom2MeanAnom, eccAnom2TrueAnom, eccLong2MeanLong, meanAnom2EccAnom, meanAnom2TrueAnom,
        meanLong2EccLong, trueAnom2MeanAnom, trueAnom2EccAnom, meanLong2TrueAnom, trueAnom2MeanLong
    )
    from resonaate.physics.math import _ATOL, wrapAngle2Pi
except ImportError as error:
    raise Exception(
        f"Please ensure you have appropriate packages installed:\n {error}"
    ) from error
# Testing Imports
from .conftest import H, K, VALLADO_AAS_COE, VALLADO_AAS_EQE
from ...conftest import BaseTestCase


class TestAnomalyConversions(BaseTestCase):
    """Test pure functions that convert between anomaly types."""

    MEAN_ANOM = deg2rad(65.10238)
    TRUE_LONG = deg2rad(69.5264380)

    # Test short circuit for circular EQE anomalies
    IS_ECC = (False, True, True, True)
    EQE_ANOM_ECC = tuple(zip(H, K, IS_ECC))

    # First case comes from Vallado Example 2-1, Others from Montenbruck Exercise 2-2
    MEAN_ANOM_CASES = deg2rad([235.4, 4, 50])
    ECC_CASES = (0.4, 0.72)
    ECC_ANOM_CASES = deg2rad([220.512074767522, rad2deg(0.24318719638), rad2deg(1.59249513093)])
    ANOM_TESTS = tuple(zip(MEAN_ANOM_CASES, ECC_CASES, ECC_ANOM_CASES))

    @pytest.mark.parametrize("anom", deg2rad([0, 1, 2, 5]))
    @pytest.mark.parametrize("h, k, is_ecc", EQE_ANOM_ECC)
    def testEQECircularCase(self, anom, h, k, is_ecc):
        """Test calculating true long of periapsis from ecc vector."""
        # pylint: disable=invalid-name
        if is_ecc:
            assert eccLong2MeanLong(anom, h, k) != anom
            assert meanLong2EccLong(anom, h, k) != anom
        else:
            assert eccLong2MeanLong(anom, h, k) == anom
            assert meanLong2EccLong(anom, h, k) == anom

    @pytest.mark.parametrize("M, ecc, E", ANOM_TESTS)
    def testMeanLong2EccLong(self, M, ecc, E):
        """Test anomaly conversion using Kepler's equation."""
        # pylint: disable=invalid-name
        raan = deg2rad(35)
        argp = deg2rad(182)
        h = ecc * sin(argp + raan)
        k = ecc * cos(argp + raan)
        lam = M + raan + argp
        F = wrapAngle2Pi(E + raan + argp)
        assert isclose(F, meanLong2EccLong(lam, h, k), rtol=0, atol=_ATOL)

    @pytest.mark.parametrize("M, ecc, E", ANOM_TESTS)
    def testEccLong2MeanLong(self, M, ecc, E):
        """Test anomaly conversion using Kepler's equation."""
        # pylint: disable=invalid-name
        raan = deg2rad(35)
        argp = deg2rad(182)
        h = ecc * sin(argp + raan)
        k = ecc * cos(argp + raan)
        lam = wrapAngle2Pi(M + raan + argp)
        F = E + raan + argp
        assert isclose(lam, eccLong2MeanLong(F, h, k), rtol=0, atol=_ATOL)

    @pytest.mark.parametrize("M, ecc, E", ANOM_TESTS)
    def testMeanAnom2EccAnom(self, M, ecc, E):
        """Test anomaly conversion using Kepler's equation."""
        # pylint: disable=invalid-name
        assert isclose(E, meanAnom2EccAnom(M, ecc), rtol=0, atol=_ATOL)

    @pytest.mark.parametrize("M, ecc, E", ANOM_TESTS)
    def testEccAnom2MeanAnom(self, M, ecc, E):
        """Test anomaly conversion."""
        # pylint: disable=invalid-name
        assert isclose(M, eccAnom2MeanAnom(E, ecc), rtol=0, atol=_ATOL)

    def testTrueAnom2EccAnom(self):
        """Test anomaly conversion."""
        # pylint: disable=invalid-name
        nu = VALLADO_AAS_COE[5]
        e = VALLADO_AAS_COE[1]
        E = meanAnom2EccAnom(self.MEAN_ANOM, e)
        assert isclose(trueAnom2EccAnom(nu, e), E, rtol=0, atol=2e-7)

    def testEccAnom2TrueAnom(self):
        """Test anomaly conversion."""
        # pylint: disable=invalid-name
        nu = VALLADO_AAS_COE[5]
        e = VALLADO_AAS_COE[1]
        E = meanAnom2EccAnom(self.MEAN_ANOM, e)
        assert isclose(eccAnom2TrueAnom(E, e), nu, rtol=0, atol=2e-7)

    def testTrueAnom2MeanAnom(self):
        """Test anomaly conversion."""
        # pylint: disable=invalid-name
        nu = VALLADO_AAS_COE[5]
        e = VALLADO_AAS_COE[1]
        assert isclose(trueAnom2MeanAnom(nu, e), self.MEAN_ANOM, rtol=0, atol=2e-7)

    def testMeanAnom2TrueAnom(self):
        """Test anomaly conversion."""
        # pylint: disable=invalid-name
        nu = VALLADO_AAS_COE[5]
        e = VALLADO_AAS_COE[1]
        assert isclose(meanAnom2TrueAnom(self.MEAN_ANOM, e), nu, rtol=0, atol=2e-7)

    def testTrueAnom2MeanLong(self):
        """Test anomaly conversion."""
        # pylint: disable=invalid-name
        nu = VALLADO_AAS_COE[5]
        e = VALLADO_AAS_COE[1]
        raan = VALLADO_AAS_COE[3]
        argp = VALLADO_AAS_COE[4]
        lam = VALLADO_AAS_EQE[5]
        assert isclose(trueAnom2MeanLong(nu, e, raan, argp, retro=True), lam, rtol=0, atol=2e-7)

    def testMeanLong2TrueAnom(self):
        """Test anomaly conversion."""
        # pylint: disable=invalid-name
        nu = VALLADO_AAS_COE[5]
        e = VALLADO_AAS_COE[1]
        raan = VALLADO_AAS_COE[3]
        argp = VALLADO_AAS_COE[4]
        lam = VALLADO_AAS_EQE[5]
        assert isclose(meanLong2TrueAnom(lam, e, raan, argp, retro=True), nu, rtol=0, atol=2e-7)
