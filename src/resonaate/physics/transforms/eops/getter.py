"""Module defining how to retrieve EOP values from various sources."""

from __future__ import annotations

# Standard Library Imports
from collections import namedtuple
from typing import TYPE_CHECKING

# Local Imports
from ....common.behavioral_config import BehavioralConfig
from .loaders import LocalDotDatEOPLoader, ModuleDotDatEOPLoader, RemoteDotDatEOPLoader

if TYPE_CHECKING:
    # Standard Library Imports
    import datetime

    # Local Imports
    from . import EarthOrientationParameter
    from .loaders import EOPLoader


LoaderTag = namedtuple("LoaderTag", ("loader_name", "loader_location"))
"""NamedTuple: Tag used to identify different :class:`.EOPLoader`'s."""

_LOADER_MAP: dict[str, EOPLoader] = {
    "ModuleDotDatEOPLoader": ModuleDotDatEOPLoader,
    "LocalDotDatEOPLoader": LocalDotDatEOPLoader,
    "RemoteDotDatEOPLoader": RemoteDotDatEOPLoader,
}
"""dict[str, EOPLoader]: Maps loader class names to loader class references."""

_EOP_LOADERS: dict[LoaderTag, EOPLoader] = {}
"""dict[LoaderTag, EOPLoader]: Stores configured loaders based on tag."""


def _loadLoader(loader_name: str | None = None, loader_location: str | None = None):
    """Return EOP loader specified by `loader_name` and `loader_location`.

    Args:
        loader_name (str, optional): Name of the concrete :class:`.EOPLoader` implementation to use.
        loader_location (str, optional): Location that the specified :class:`.EOPLoader` will load
            EOP data from.

    Returns:
        EOPLoader: :class:`.EOPLoader` object specified by `loader_name` and `loader_location`.
    """
    behave_config = BehavioralConfig.getConfig()
    if loader_name is None:
        loader_name = behave_config.eop.LoaderName

    if loader_location is None:
        loader_location = behave_config.eop.LoaderLocation

    tag = LoaderTag(loader_name, loader_location)
    loader = _EOP_LOADERS.get(tag)
    if not loader:
        try:
            loader = _LOADER_MAP[loader_name](loader_location)
        except KeyError:
            err = f"Specified loader '{loader_name}' is undefined"
            raise ValueError(err)  # noqa: B904
        _EOP_LOADERS[tag] = loader
    return loader


def getEarthOrientationParameters(
    eop_date: datetime.date,
    loader_name: str | None = None,
    loader_location: str | None = None,
) -> EarthOrientationParameter:
    """Return the :class:`.EarthOrientationParameter` for the specified calendar date.

    Args:
        eop_date (``datetime.date``): Date at which to get EOP values.
        loader_name (str, optional): Name of the concrete :class:`.EOPLoader` implementation to use.
        loader_location (str, optional): Location that the specified :class:`.EOPLoader` will load
            EOP data from.

    See Also:
        Default values obtained from Celestrak.com

    Returns:
        :class:`.EarthOrientationParameter`: EOP values for the specified calendar date.

    Raises:
        MissingEOP: If the configured EOP data does not have information for the specified calendar
            date.
    """
    loader = _loadLoader(loader_name, loader_location)
    return loader.getEarthOrientationParameters(eop_date)


def setEarthOrientationParameters(
    eop_date: datetime.date,
    eop_data: EarthOrientationParameter,
    loader_name: str | None = None,
    loader_location: str | None = None,
):
    """Set specific EOP data for the specified `eop_date`.

    Args:
        eop_date (datetime.date): Date to set EOP data for.
        eop_data (EarthOrientationParameter): The EOP data specified for `eop_date`.
        loader_name (str, optional): Name of the concrete :class:`.EOPLoader` implementation to use.
        loader_location (str, optional): Location that the specified :class:`.EOPLoader` will load
            EOP data from.
    """
    loader = _loadLoader(loader_name, loader_location)
    loader.setEOPData(eop_date, eop_data)
