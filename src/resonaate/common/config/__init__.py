"""Module defining common configuration formats."""
from __future__ import annotations

# Standard Library Imports
from argparse import ArgumentParser, RawTextHelpFormatter

# Third Party Imports
from pydantic import BaseModel

# Local Imports
from .behavioral import BehavioralConfig
from .input_output import IOConfiguration
from .meta import NotSet, userSpecFactory


class RootConfig(BaseModel):

    io_config: IOConfiguration

    behavioral_config: BehavioralConfig = BehavioralConfig()

    @classmethod
    def getCommandLineParser(cls) -> ArgumentParser:
        """Build command line argument parser based on :class:`.BehaviroalConfig`."""
        parser = ArgumentParser(
            description="RESONAATE Command Line Interface",
            argument_default=NotSet,
            formatter_class=RawTextHelpFormatter,
        )
        user_spec = userSpecFactory("root", cls)
        user_spec.addToArgParser(parser)
        return parser
