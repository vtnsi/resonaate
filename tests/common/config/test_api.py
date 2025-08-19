from __future__ import annotations

# Third Party Imports
import pytest

# RESONAATE Imports
from resonaate.common.config import EntrypointConfig, LibraryConfig, RootConfig


def test_getEntryConfig(put_main_init_arg):
    """Validate that :class:`.EntrypointConfig` builds successfully."""
    cfg = RootConfig.ENTRY.inst()
    assert isinstance(cfg, EntrypointConfig)

    # make sure singleton works as expected
    dup_cfg = RootConfig.ENTRY.inst()
    assert dup_cfg is cfg


def test_getEntryConfig_noInit():
    """Validate that error is thrown when trying to build :class:`.EntrypointConfig` without init message arg."""
    with pytest.raises(SystemExit):
        _ = RootConfig.ENTRY.inst()


def test_getLibConfig():
    """Validate that :class:`.LibraryConfig` builds successfully."""
    cfg = RootConfig.LIB.inst()
    assert isinstance(cfg, LibraryConfig)

    # make sure singleton works as expected
    dup_cfg = RootConfig.LIB.inst()
    assert dup_cfg is cfg


def test_getLibConfig_withInit(put_main_init_arg):
    """Validate that :class:`.LibraryConfig` builds successfully even when an init arg is provided."""
    cfg = RootConfig.LIB.inst()
    assert isinstance(cfg, LibraryConfig)

    # make sure singleton works as expected
    dup_cfg = RootConfig.LIB.inst()
    assert dup_cfg is cfg
