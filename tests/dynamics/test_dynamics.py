"""Test Dynamics module."""

from __future__ import annotations

# Third Party Imports
from numpy import asarray
from scipy.linalg import norm

# RESONAATE Imports
from resonaate.dynamics.special_perturbations import SpecialPerturbations
from resonaate.dynamics.two_body import TwoBody
from resonaate.physics.bodies import Earth
from resonaate.physics.time.stardate import JulianDate
from resonaate.scenario.config.geopotential_config import GeopotentialConfig
from resonaate.scenario.config.perturbations_config import PerturbationsConfig


class TestDynamics:
    """Dynamics test class."""

    stable_orbit = asarray([41574.6, 6681.53, 0, -0.485045, 3.03858, 0])
    crash_orbit = asarray([6088.234341, 50.29079, 8.763258, -1.999674, 6.626409, 3.597847])

    julian_date = JulianDate(2459690.58116)

    def testEarthCrash(self):
        """Test to make sure an assert is raised if a RSO crashes into the Earth."""
        assert norm(self.stable_orbit[:3]) > Earth.radius
        assert norm(self.crash_orbit[:3]) < Earth.radius

    def testTwoBodyPropagation(self):
        """Test TwoBody dynamics."""
        dynamics = TwoBody()
        final_state = dynamics.propagate(
            initial_time=0.0,
            final_time=60.0,
            initial_state=self.stable_orbit,
        )

        assert final_state.shape == (6,)

    def testGeopotentialPropagation(self):
        """Test geopotential with no perturbations."""
        geopotential = GeopotentialConfig(degree=2, order=2)
        perturbations = PerturbationsConfig()
        dynamics = SpecialPerturbations(self.julian_date, geopotential, perturbations, 1)

        _ = dynamics.propagate(initial_time=0.0, final_time=60.0, initial_state=self.stable_orbit)

    def testThirdBodyPropagation(self):
        """Test third body propagation."""
        geopotential = GeopotentialConfig(degree=0, order=0)
        perturbations = PerturbationsConfig(third_bodies=["sun", "moon"])

        dynamics = SpecialPerturbations(self.julian_date, geopotential, perturbations, 1)
        _ = dynamics.propagate(initial_time=0.0, final_time=60.0, initial_state=self.stable_orbit)

    def testSolarRadiationPressurePropagation(self):
        """Test SRP perturbations with no geopotential."""
        geopotential = GeopotentialConfig(degree=0, order=0)
        perturbations = PerturbationsConfig(solar_radiation_pressure=True)

        dynamics = SpecialPerturbations(self.julian_date, geopotential, perturbations, 1)
        _ = dynamics.propagate(initial_time=0.0, final_time=60.0, initial_state=self.stable_orbit)

    def testRelativityPropagation(self):
        """Test general relativity perturbation."""
        geopotential = GeopotentialConfig(degree=0, order=0)
        perturbations = PerturbationsConfig(general_relativity=True)

        dynamics = SpecialPerturbations(self.julian_date, geopotential, perturbations, 1)
        _ = dynamics.propagate(initial_time=0.0, final_time=60.0, initial_state=self.stable_orbit)

    def testEveryPerturbationPropagation(self):
        """Test that propagation works with every perturbation turned on."""
        geopotential = GeopotentialConfig(degree=2, order=2)
        perturbations = PerturbationsConfig(
            third_bodies=["sun", "moon", "venus", "jupiter"],
            solar_radiation_pressure=True,
            general_relativity=True,
        )

        dynamics = SpecialPerturbations(self.julian_date, geopotential, perturbations, 1)
        _ = dynamics.propagate(initial_time=0.0, final_time=60.0, initial_state=self.stable_orbit)
