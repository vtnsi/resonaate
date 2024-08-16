from __future__ import annotations

# Standard Library Imports
import datetime
from abc import ABC, abstractmethod
from importlib import resources
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlopen

# Local Imports
from ....common.utilities import loadDatFile
from ... import constants as const
from . import EarthOrientationParameter, MissingEOP


class EOPLoader(ABC):
    """Abstract class defining how Earth Orientation Parameters should be loaded."""

    def __init__(self, location: str):
        """
        Args:
            location (str): Specifies where the EOP content to loaded is located.
        """
        self._location = location
        self._eop_data: dict[datetime.date, EarthOrientationParameter] = {}
        self._is_loaded = False

    def getEarthOrientationParameters(self, eop_date: datetime.date) -> EarthOrientationParameter:
        """Return the :class:`.EarthOrientationParameter` for the specified `eop_date`.

        Args:
            eop_date (``datetime.date``): date at which to get EOP values.

        Returns:
            :class:`.EarthOrientationParameter`: EOP values valid for specified `eop_date`.
        """
        if not self._is_loaded:
            self.load()

        eop = self._eop_data.get(eop_date)
        if eop is None:
            err = f"Could not retrieve EOP data for specified date: {eop_date}"
            raise MissingEOP(err)
        # else:
        return eop

    @abstractmethod
    def load(self):
        """Load the EOP content into local memory.

        A concrete implementation of this method should set the :attr:`._is_loaded` to ``True``.
        """
        raise NotImplementedError()


class DotDatEOPLoader(EOPLoader, ABC):
    """Abstract interface defining how to properly load a '.dat' EOP data file."""

    RAD2ARCSEC = const.RAD2SEC * const.SEC2ARCSEC
    """float: Constant value used to convert radians to arc seconds."""

    def _parseDatData(self, raw_data: list[list[float]]):
        """Loads the specified `raw_data` into local memory.

        Args:
            raw_data (list[list[float]]): EOP data file contents parsed using
                :meth:`.loadDatFile()`.
        """
        for eop in raw_data:
            eop_date = datetime.date(int(eop[0]), int(eop[1]), int(eop[2]))
            self._eop_data[eop_date] = EarthOrientationParameter(
                date=eop_date,
                x_p=eop[4] * const.ARCSEC2RAD,
                y_p=eop[5] * const.ARCSEC2RAD,
                d_delta_psi=eop[8] * const.ARCSEC2RAD,
                d_delta_eps=eop[9] * const.ARCSEC2RAD,
                delta_ut1=eop[6],
                length_of_day=eop[7],
                delta_atomic_time=int(eop[12]),
            )
        self._is_loaded = True

    def _unparseDatData(self, eops: list[EarthOrientationParameter]) -> list[str]:
        """Dumps the specified `eops` into a raw '.dat' data format.

        Args:
            eops (list[EarthOrientationParameter]): List of Earth orientation parameters to dump to
                raw data format.

        Returns:
            list[str]: Raw '.dat' data format to potentially be saved to persistent memory.
        """
        raw_data = []
        for eop in eops:
            raw_data.append("{d} {d} {d} {d} {: f} {: f} {: f} {: f} {: f} {: f} {: f} {: f} {: f}".format(
                eop.date.year,
                eop.date.month,
                eop.date.day,
                0,  # mjd
                eop.x_p * self.RAD2ARCSEC,
                eop.y_p * self.RAD2ARCSEC,
                eop.delta_ut1,
                eop.length_of_day,
                0.0,  # dX
                0.0,  # dY
                eop.d_delta_psi * self.RAD2ARCSEC,
                eop.d_delta_eps * self.RAD2ARCSEC,
                eop.delta_atomic_time
            ))
        return raw_data


class ModuleDotDatEOPLoader(DotDatEOPLoader):
    """Concrete class defining how EOPs should be loaded as a Python module resource."""

    EOP_MODULE: str = "resonaate.physics.data.eop"
    """``str``: defines EOP data module location."""

    def load(self):
        res = resources.files(self.EOP_MODULE).joinpath(self._location)
        with resources.as_file(res) as file_resource:
            raw_data = loadDatFile(file_resource)
        self._parseDatData(raw_data)


class LocalDotDatEOPLoader(DotDatEOPLoader):
    """Concrete class defining how EOPs should be loaded as a local '.dat' file."""

    def __init__(self, location: str):
        """
        Args:
            location (str): Specifies where the EOP content to loaded is located.
        """
        super().__init__(location)
        self._path = Path(self._location)

    def load(self):
        """Load the EOP content into local memory.

        A concrete implementation of this method should set the :attr:`._is_loaded` to ``True``.
        """
        raw_data = loadDatFile(self._path)
        self._parseDatData(raw_data)


class RemoteDotDatEOPLoader(DotDatEOPLoader):
    """Concrete class defining how EOPs should be loaded from a remote '.dat' file."""

    CACHE_LOCATION = Path("~/.resonaate/eop-cache/").expanduser()
    """Path: Path to directory that remote files are cached in."""

    def __init__(self, location: str, clear_cache: bool = False):
        """
        Args:
            location (str): URL to remote EOP data file.
            clear_cache (bool,optional): Flag indicating whether to clear the cached EOP data file
                to force pulling data from the URL.
        """
        super().__init__(location)
        self._parsed_url = urlparse(self._location)
        if not self._parsed_url.netloc:
            err = f"Unable to parse URL: {self._location}"
            raise ValueError(err)

        fs_safe_netloc = self._parsed_url.netloc.replace(".", "_")
        fs_safe_url_path = self._parsed_url.path
        if fs_safe_url_path.startswith("/"):
            fs_safe_url_path = fs_safe_url_path[1:]
        self._cache_path = self.CACHE_LOCATION / fs_safe_netloc / fs_safe_url_path
        if clear_cache:
            self._cache_path.unlink(missing_ok=True)

    def load(self):
        """Load the EOP content into local memory.

        A concrete implementation of this method should set the :attr:`._is_loaded` to ``True``.
        """
        if not self._cache_path.exists():
            self._cache_path.parent.mkdir(parents=True, exist_ok=True)
            with urlopen(self._location) as remote_data:
                with open(self._cache_path, "wb") as cache_file:
                    for line in remote_data:
                        try:
                            parsed = [float(x) for x in line.split()]
                        except ValueError:
                            continue
                        if parsed:
                            cache_file.write(line)

        raw_data = loadDatFile(self._cache_path)
        self._parseDatData(raw_data)