"""Contains all the custom-defined exceptions used in RESONAATE."""
# Standard Library Imports
# Pip Package Imports
# RESONAATE Imports


class TaskTimeoutError(Exception):
    """Exception indicating tasks haven't completed within a given timeout."""


class ShapeError(BaseException):
    """Exception indicating an improperly shaped matrix was created."""


class MissingEphemerisError(BaseException):
    """Exception indicating that there is a missing :class:`.TruthEphemeris` in the database."""
