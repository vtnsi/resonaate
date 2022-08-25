from __future__ import annotations

# RESONAATE Imports
from resonaate.physics.transforms.nutation import get1980NutationSeries


def testNutation1980Series():
    """Test loading nutation files."""
    r_c, i_c = get1980NutationSeries()
    assert r_c.shape == (106, 4)
    assert i_c.shape == (106, 5)
