"""Contains all the custom-defined exceptions used in RESONAATE."""
# Standard Library Imports
# Pip Package Imports
# RESONAATE Imports


class JobTimeoutError(Exception):
    """Exception indicating jobs haven't completed within a given timeout."""


class ShapeError(Exception):
    """Exception indicating an improperly shaped matrix was created."""


class MissingEphemerisError(Exception):
    """Exception indicating that there is a missing :class:`.TruthEphemeris` in the database."""
