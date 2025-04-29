"""Contains classes and functions used across all other packages."""

from __future__ import annotations

from datetime import datetime


def timeStampPath(fmt_path: str, now: datetime | None = None) -> str:
    """Add a filename-safe timestamp to `fmt_path`.

    Args:
        fmt_path: Path to add a timestamp to. Filename portion of path should include format
            brackets ``{}`` where timestamp will be insertted.
        now: The datetime to make the timestamp from. If left unspecified, ``datetime.now()`` will
            be used.

    Returns:
        File path string with timestamp added to.
    """
    if now is None:
        now = datetime.now()
    timestamp = now.isoformat().replace(":", "-").replace(".", "")
    fmt_path.format(timestamp)
    return fmt_path
