"""Contains classes and functions used across all other packages."""

from __future__ import annotations

from datetime import datetime


def pathSafeTime(dt: datetime | None = None) -> str:
    """Return a path-safe string representation of `dt`.

    Args:
        dt: The date and time to generate a path-safe time stamp from.

    Returns:
        A path-safe string representation of `dt`.
    """
    if dt is None:
        dt = datetime.now()
    return dt.isoformat().replace(":", "-").replace(".", "")
