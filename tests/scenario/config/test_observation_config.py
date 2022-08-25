from __future__ import annotations

# RESONAATE Imports
from resonaate.scenario.config.observation_config import ObservationConfig


def testObservationConfig():
    """Test that ObservationConfig can be created from a dictionary."""
    cfg = ObservationConfig(field_of_view=True)
    assert cfg.field_of_view is True
