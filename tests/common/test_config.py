from __future__ import annotations

from resonaate.common.config import RootConfig, getConfig, putResonaateArgs


def test_getConfig():
    """Initial test of 'end-to-end' config pipeline."""
    putResonaateArgs(["configs/json/main_init.json"])
    cfg = getConfig()
    assert isinstance(cfg, RootConfig)
