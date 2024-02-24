"""Contains all the custom-defined exceptions used in RESONAATE."""

from __future__ import annotations


class JobProcessingError(Exception):
    """Exception indicating jobs encountered an error during processing."""


class AgentProcessingError(JobProcessingError):
    """Error occurred during parallel processing of an Agent object."""


class ShapeError(Exception):
    """Exception indicating an improperly shaped matrix was created."""


class MissingEphemerisError(Exception):
    """Exception indicating that there is a missing :class:`.TruthEphemeris` in the database."""


class DuplicateTargetError(Exception):
    """Exception that occurs for conflicting duplicate targets."""


class DuplicateSensorError(Exception):
    """Exception that occurs for duplicate sensors."""


class DuplicateEngineError(Exception):
    """Exception that occurs for duplicate engines."""
