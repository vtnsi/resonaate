# pylint: disable=protected-access
from __future__ import annotations

# Standard Library Imports
from datetime import timedelta

# Third Party Imports
import pytest

# Local Imports
from .. import FIXTURE_DATA_DIR, PropagateFunc


@pytest.mark.estimation()
@pytest.mark.integration()
class TestAdaptiveEstimationIntegration:
    """Integration test :class:`.AdaptiveFilter` classes."""

    @pytest.mark.slow()
    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testStaticMultipleModel(self, datafiles: str, propagate_scenario: PropagateFunc):
        """Test the static multiple model and mmae running over multiple timesteps."""
        init_filepath = "smm_init.json"
        elapsed_time = timedelta(hours=5)
        propagate_scenario(datafiles, init_filepath, elapsed_time)

    @pytest.mark.slow()
    @pytest.mark.datafiles(FIXTURE_DATA_DIR)
    def testGeneralizedPseudoBayesianFirstOrderModel(
        self, datafiles: str, propagate_scenario: PropagateFunc
    ):
        """Test the gpb1 and mmae converging on a single timestep."""
        init_filepath = "gpb1_init.json"
        elapsed_time = timedelta(hours=3)
        propagate_scenario(datafiles, init_filepath, elapsed_time)
