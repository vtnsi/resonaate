"""Contains all the custom-defined exceptions used in RESONAATE."""
# Standard Library Imports
# Pip Package Imports
# RESONAATE Imports


class JobTimeoutError(Exception):
    """Exception indicating jobs haven't completed within a given timeout."""


class JobProcessingError(Exception):
    """Exception indicating jobs encountered an error during processing."""


class AgentProcessingError(JobProcessingError):
    """Error occurred during parallel processing of an Agent object."""


class ShapeError(Exception):
    """Exception indicating an improperly shaped matrix was created."""


class MissingEphemerisError(Exception):
    """Exception indicating that there is a missing :class:`.TruthEphemeris` in the database."""
