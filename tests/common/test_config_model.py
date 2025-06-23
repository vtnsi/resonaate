
# Standard Library Imports
from pathlib import Path

# Third Party Imports
import pytest

# RESONAATE Imports
from resonaate.common.config import RootConfig, userSpecFactory


def test_getArgParser():
    parser = RootConfig.getCommandLineParser()
    parser.print_help()
