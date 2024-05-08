"""Provides classes for third bodies utilized in RESONAATE.

The classes utilize JPL Horizons data to provide extremely accurate state data
for Solar System bodies. It uses JPL Horizons ephemeris files saved to ``numpy``
arrays, and then directly implements the Chebyshev coefficient interpolation
scheme.

To save data from a new kernel, the code expects that all ``numpy`` coefficient
arrays are stored in **.npy** files under a directory with the name of the
kernel file. For example, ``'de432s'`` is the current default kernel and it
has all its segment coefficient arrays under **physics/data/de432s/**.

The naming scheme of these files is also important; the format is
expected to be: ``c-t-e-i.npy`` where ``c`` is the index of the center
body, ``t`` is the index of the target body, ``e`` is the initial epoch
as a Julian date, and ``i`` is the segment interval length in Julian days.

Here is an example of how to load a kernel segment's data directly, and save
it to a file. This assumes the file **de432s.bsp** is in the repo root
directory, and that there is a directory called
**src/resonaate/physics/data/de432s** relative to the repo root.

.. code-block:: python

    from jplephem.spk import SPK
    import numpy as np

    kernel_name = 'de432s'
    binary_name = kernel_name + '.bsp'

    kernel = SPK.open(binary_name)
    init_e, int_len, coeff = kernel[0, 10].load_array()

    seg_name = 'src/resonaate/physics/data/' + kernel_name + '/'
    seg_name += f'0-10-{init_e}-{int_len}.npy'
    with open(seg_name, 'wb') as f:
        np.save(f, np.array(coeff))

    kernel.close()

This loads the `10`-th body's position relative to the `0`-th body, and
stores the initial epoch in ``init_e``, the interval length in ``int_len``,
and the actual Chebyshev coefficients in ``coeff``.

If adding a data from a new kernel, users should also define the kernel map.
This ensures that the kernel loads and is indexed in the same format as all
other kernels, meaning that segment calculations don't need to change for
different kernel formats. See :data:`.KERNEL_MAP` and :class:`.TBK` source
code for details on the implementation.

Todo:
    - Make the third body ephemeris file loading configurable
    - Allow for kernels included in and not in resonaate package

See Also:
    #. `Horizons SPK <SPK>`_: for more information on the binary files.
    #. `jplephem`_: for information on using kernels and retrieving their data.
    #. Snippet `$275 <snippet-275>`_ for an example of generating unit test data

.. _SPK:
    https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/planets/
.. _jplephem:
    https://pypi.org/project/jplephem/
.. _snippet-275:
    https://code.vt.edu/space-research/resonaate/resonaate/-/snippets/275
.. _chebval:
    https://numpy.org/devdocs/reference/generated/numpy.polynomial.chebyshev.chebval.html#numpy.polynomial.chebyshev.chebval
.. _mapdomain:
    https://numpy.org/devdocs/reference/generated/numpy.polynomial.polyutils.mapdomain.html#numpy.polynomial.polyutils.mapdomain
.. _mapparms:
    https://numpy.org/devdocs/reference/generated/numpy.polynomial.polyutils.mapparms.html#numpy.polynomial.polyutils.mapparms
"""

from __future__ import annotations

# Standard Library Imports
from abc import ABC, abstractmethod
from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum
from functools import lru_cache
from importlib import resources
from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple, Union

# Third Party Imports
from numpy import array, load
from numpy.polynomial.chebyshev import chebval

# Type Checking Imports
if TYPE_CHECKING:
    # Third Party Imports
    from numpy import ndarray


THIRD_BODY_KERNEL = "de432s"
"""``str``: define the kernel to use for third body perturbations."""


class ThirdBodyTuple(NamedTuple):
    """Named tuple for holding metadata and coefficients related to third body ephemeris interpolation.

    Attributes:
        center (``int``): integer describing the center body of the kernel segment.
        target (``int``): integer describing the target body of the kernel segment.
        init_epoch (``float``): Julian date of the initial epoch that is valid for this segment.
        interval (``float``): number of Julian days that each sub-segment is valid for.
        coefficients (``ndarray``): Chebyshev coefficients for each sub-segment.
    """

    center: int
    target: int
    init_epoch: float
    interval: float
    coefficients: ndarray


class TBK(Enum):
    """Enum describing the common index for each kernel segment.

    This allows different kernels to map segments to the same order.
    """

    SS_BC_2_MERCURY_BC = 0
    SS_BC_2_VENUS_BC = 1
    SS_BC_2_EARTH_BC = 2
    SS_BC_2_MARS_BC = 3
    SS_BC_2_JUPITER_BC = 4
    SS_BC_2_SATURN_BC = 5
    SS_BC_2_URANUS_BC = 6
    SS_BC_2_NEPTUNE_BC = 7
    SS_BC_2_PLUTO_BC = 8
    SS_BC_2_SUN_CENTER = 9
    EARTH_BC_2_MOON_CENTER = 10
    EARTH_BC_2_EARTH_CENTER = 11
    MERCURY_BC_2_MERCURY_CENTER = 12
    VENUS_BC_2_VENUS_CENTER = 13

    def __lt__(self, other):
        """Explicitly define less than for use in sorting kernel segments."""
        msg = f"Can only compare a TBK enum to another: {type(other)}"
        if not isinstance(other, TBK):
            raise TypeError(msg)
        return int(self.value) < int(other.value)


KERNEL_MAP: dict[str, dict[tuple[int, int], TBK]] = {
    "de432s": {
        (0, 1): TBK.SS_BC_2_MERCURY_BC,
        (0, 2): TBK.SS_BC_2_VENUS_BC,
        (0, 3): TBK.SS_BC_2_EARTH_BC,
        (0, 4): TBK.SS_BC_2_MARS_BC,
        (0, 5): TBK.SS_BC_2_JUPITER_BC,
        (0, 6): TBK.SS_BC_2_SATURN_BC,
        (0, 7): TBK.SS_BC_2_URANUS_BC,
        (0, 8): TBK.SS_BC_2_NEPTUNE_BC,
        (0, 9): TBK.SS_BC_2_PLUTO_BC,
        (0, 10): TBK.SS_BC_2_SUN_CENTER,
        (3, 301): TBK.EARTH_BC_2_MOON_CENTER,
        (3, 399): TBK.EARTH_BC_2_EARTH_CENTER,
        (1, 199): TBK.MERCURY_BC_2_MERCURY_CENTER,
        (2, 299): TBK.VENUS_BC_2_VENUS_CENTER,
    },
}
"""``dict``: map describing how the (center, target) pairs of a kernel map to common tuple index."""


def readKernelSegmentFile(kernel_module: str, filename: str | Path) -> ThirdBodyTuple:
    """Read kernel segment from a numpy array file.

    Args:
        kernel_module (``str``): module in which the kernel segment files are located.
        filename (``str`` | ``Path``): file in which kernel segment data is located.

    Returns:
        :class:`.ThirdBodyTuple`: kernel segment metadata and data.
    """
    # Parse metadata from filename
    filepath = Path(filename)
    metadata = filepath.stem.split("-")
    center, target = int(metadata[0]), int(metadata[1])
    init_jd, interval = float(metadata[2]), float(metadata[3])

    # Get coefficient array
    res = resources.files(kernel_module).joinpath(filename)
    with resources.as_file(res) as kernel_file, open(kernel_file, "rb") as segment_file:
        coefficients = load(segment_file)

    return ThirdBodyTuple(center, target, init_jd, interval, coefficients)


def readKernelSegments(kernel_module: str) -> list[ThirdBodyTuple]:
    """Read kernel segments from a given directory.

    Args:
        kernel_module (``str``): module in which the kernel segment files are located.

    Returns:
        ``list``: :class:`.ThirdBodyTuple` objects describing each kernel segment.
    """
    kernel_segments = []
    kernel_files = [res.name for res in resources.files(kernel_module).iterdir() if res.is_file()]
    for filename in kernel_files:
        filepath = Path(filename)
        # Only parse .npy files
        ext = filepath.suffix
        if ext.lower() != ".npy":
            continue
        kernel_segments.append(readKernelSegmentFile(kernel_module, filepath))

    return kernel_segments


@lru_cache(maxsize=5)
def loadKernelData(kernel_name: str) -> tuple[tuple[float, float, ndarray], ...]:
    """Load JPL Horizons kernel data from files into global tuple.

    Args:
        kernel_name (``str``): name of JPL ephemeris kernel to load data from.

    Returns:
        ``tuple``: initial epoch, interval, and coefficient information for each kernel segment.
    """
    kernel_module = f"resonaate.physics.data.{kernel_name}"
    kernel_segments = readKernelSegments(kernel_module)

    # Sort segments according to TBK enum
    segment_map: dict[tuple[int, int], TBK] = KERNEL_MAP[kernel_name]
    sorted_segments = sorted(
        kernel_segments,
        key=lambda segment: segment_map[(segment.center, segment.target)],
    )
    return tuple(
        (segment.init_epoch, segment.interval, segment.coefficients) for segment in sorted_segments
    )


THIRD_BODY_EPHEMS: tuple[tuple[float, float, ndarray], ...] = loadKernelData(THIRD_BODY_KERNEL)
"""``tuple``: tuples containing initial epoch, interval, and coefficient information for each kernel segment."""


IterFloatType = Union[float, Iterable[float]]
"""Type alias for parameter that can be either a float _or_ an iterable of floats."""


def _scaleChebyshevInputs(
    jd: IterFloatType,
    init_jd: float,
    int_length: float,
) -> tuple[ndarray, ndarray]:
    """Scale the input(s) for a Chebyshev series based to a domain of :math:`[-1, 1]`.

    If ``jd`` is an iterable, then the function returns the properly scaled points and corresponding indices
    for each given ``jd``. The evaluation of the Chebyshev series requires that the domain of input points is
    :math:`[-1, 1]`. This function properly scales the Julian dates to the correct values in this domain.

    Note:
        JPL Horizons kernel segments are split into many Chebyshev series in order to best approximate positions
        over very long time frames. Therefore, this scaling function is unique to this module, so we may scale
        multiple input values at once that aren't necessarily in the same series set (and therefore aren't in
        the same domain).

    See Also:
        #. `chebval() <chebval>`_: For details on Chebyshev series evaluation
        #. `mapdomain() <mapdomain>`_ For details on scaling input points
        #. `mapparms() <mapparms>`_ For details on mapping domains

    Args:
        jd (``float`` | ``Iterable``): :math:`N` epoch(s) at which the position is to be calculated (Julian date).
        init_jd (``float``): Initial epoch of the entire set of JPL Horizons Chebyshev series (Julian date).
        int_length (``float``): Valid length of each Chebyshev series (Julian days).

    Returns:
        ``tuple(ndarray, ndarray)``: the scaled Julian date and corresponding index arrays
    """
    jd = array(jd, copy=True)
    val: ndarray = (jd - init_jd) / int_length
    idx: ndarray = array(val, dtype=int)
    scaled_jd: ndarray = 2 * (val - idx - 0.5)

    return scaled_jd, idx


def getSegmentPosition(jd: IterFloatType, segment: TBK) -> ndarray:
    r"""Get the position of a Horizons segment body using Chebyshev coefficients.

    If ``jd`` is an iterable, then the function returns the segment position vectors at each Julian date.
    The evaluation of the chebyshev series uses Clenshaw recursion, and the function used requires the
    domain to be :math:`[-1, 1]`. Therefore we scale the input Julian date(s) to the proper domain.

    See Also:
        #. `chebval() <chebval>`_: For details on Chebyshev evaluation
        #. :func:`._scaleChebyshevInputs`: for details on scaling the input Julian dates

    Args:
        jd (``float`` | ``Iterable``): :math:`N` epoch(s) at which the position is to be calculated, Julian dates.
        segment (:class:`.TBK`): Horizons ephemeris kernel segment for which position is calculated.

    Returns:
        ``ndarray``: 3x1 | Nx3 position vector(s) of the specified segment, where :math:`N` is the
        number of ``jd`` values entered (km).
    """
    # Initial epoch as Julian date
    jd0: float
    # Segment interval length in Julian days
    interval: float
    # Chebyshev series coefficients for x, y, z components
    coefficients: ndarray
    # Unpack metadata from desired ephemeris segment
    jd0, interval, coefficients = THIRD_BODY_EPHEMS[segment.value]

    # Calculate the corresponding index to retrieve the correct set of coefficients.
    scaled_jd, idx = _scaleChebyshevInputs(jd, jd0, interval)

    # [NOTE]: Coefficient (degree) index must be first for `chebval()`, so coefficient matrices are transposed.
    #   Also, we want to be able to account for any set of Julian dates, which means that possibly different
    #   Chebyshev series coefficient sets are valid and therefore possibly different domains are needed. This
    #   requires looping rather than a direct call.
    if isinstance(scaled_jd, Iterable):
        return array(
            tuple(chebval(jd, coefficients[:, ii, :].T) for jd, ii in zip(scaled_jd, idx)),
        )

    # else
    return chebval(scaled_jd, coefficients[:, idx, :].T)


@dataclass
class ThirdBody(ABC):
    r"""Base class for third body objects.

    Attributes:
        mu (``float``): gravitational parameter, (km^3/sec^2).
    """

    mu: float

    @staticmethod
    @abstractmethod
    def getPosition(jd: float) -> ndarray:
        """Calculate the ECI/J2000 position of the body's center at an epoch relative to the Earth.

        Args:
            jd (``float`` | ``Iterable``): :math:`N` epoch(s) at which the position is to be calculated (Julian date).

        Returns:
            ``ndarray``: 3x1 | Nx3 ECI position vector(s) of the body, where :math:`N` is the
            number of ``jd`` values entered (km).
        """
        raise NotImplementedError


class Sun(ThirdBody):
    r"""Sun third body class.

    Attributes:
        mu (``float``): gravitational parameter (km^3/sec^2), from DE430.
        radius (``float``): mean equatorial radius (km), from Vallado.
        mass (``float``): sun's mass (kg), from Vallado.
        absolute_magnitude (``float``): sun's absolute visual magnitude (unitless) from NASA.

    References:
        :cite:t:`vallado_2013_astro`, Appendix D.3, Table D-5.
        :cite:t:`folkner_2014_planetary`, Table 8.
        :cite:t:`sun_vismag_2018_nasa`
    """

    mu: float = 1.32712440041939400e11
    radius: float = 696000.0
    mass: float = 1.9891e30
    absolute_magnitude = -26.74

    @staticmethod
    def getPosition(jd: float) -> ndarray:
        """Calculate the ECI/J2000 position of the Sun's center at an epoch relative to the Earth.

        Args:
            jd (``float`` | ``Iterable``): :math:`N` epoch(s) at which the position is to be calculated (Julian date).

        Returns:
            ``ndarray``: 3x1 | Nx3 ECI position vector(s) of the Sun, where :math:`N` is the
            number of ``jd`` values entered (km).
        """
        # SS BC to Sun center - SS BC to Earth BC - Earth BC to Earth Center
        position = getSegmentPosition(jd, TBK.SS_BC_2_SUN_CENTER)
        position -= getSegmentPosition(jd, TBK.SS_BC_2_EARTH_BC)
        position -= getSegmentPosition(jd, TBK.EARTH_BC_2_EARTH_CENTER)
        return position


class Moon(ThirdBody):
    r"""Moon third body class.

    Attributes:
        mu (``float``): gravitational parameter, (km^3/sec^2), from DE430.
        radius (``float``): mean equatorial radius (km), from Vallado.
        mass (``float``): moon's mass (kg), from Vallado.

    References:
        :cite:t:`vallado_2013_astro`, Appendix D.3, Table D-3.
        :cite:t:`folkner_2014_planetary`, Table 8.
    """

    mu: float = 4902.800066
    radius: float = 1738.0
    mass: float = 7.3483e22

    @staticmethod
    def getPosition(jd: float) -> ndarray:
        """Calculate the ECI/J2000 position of the Moon's center at an epoch relative to the Earth.

        Args:
            jd (``float`` | ``Iterable``): :math:`N` epoch(s) at which the position is to be calculated (Julian date).

        Returns:
            ``ndarray``: 3x1 | Nx3 ECI position vector(s) of the Moon, where :math:`N` is the
            number of ``jd`` values entered (km).
        """
        # Earth BC to Moon center - Earth BC to Earth Center
        position = getSegmentPosition(jd, TBK.EARTH_BC_2_MOON_CENTER)
        position -= getSegmentPosition(jd, TBK.EARTH_BC_2_EARTH_CENTER)
        return position


class Jupiter(ThirdBody):
    r"""Jupiter third body class.

    Attributes:
        mu (``float``): gravitational parameter, (km^3/sec^2), from DE430.
        radius (``float``): mean equatorial radius (km), from Vallado.
        mass (``float``): planet's mass (kg), from Vallado.

    References:
        :cite:t:`vallado_2013_astro`, Appendix D.3, Table D-3.
        :cite:t:`folkner_2014_planetary`, Table 8.
    """

    mu: float = 1.267127641e8
    radius: float = 71492.0
    mass: float = 18988e27

    @staticmethod
    def getPosition(jd: float) -> ndarray:
        """Calculate the ECI/J2000 position of Jupiter's center at an epoch relative to the Earth.

        Args:
            jd (``float`` | ``Iterable``): :math:`N` epoch(s) at which the position is to be calculated (Julian date).

        Returns:
            ``ndarray``: 3x1 | Nx3 ECI position vector(s) of Jupiter, where :math:`N` is the
            number of ``jd`` values entered (km).
        """
        # SS BC to Jupiter center - SS BC to Earth BC - Earth BC to Earth Center
        position = getSegmentPosition(jd, TBK.SS_BC_2_JUPITER_BC)
        position -= getSegmentPosition(jd, TBK.SS_BC_2_EARTH_BC)
        position -= getSegmentPosition(jd, TBK.EARTH_BC_2_EARTH_CENTER)
        return position


class Saturn(ThirdBody):
    r"""Saturn third body class.

    Attributes:
        mu (``float``): gravitational parameter, (km^3/sec^2), from DE430.
        radius (``float``): mean equatorial radius (km), from Vallado.
        mass (``float``): planet's mass (kg), from Vallado.

    References:
        :cite:t:`vallado_2013_astro`, Appendix D.3, Table D-3.
        :cite:t:`folkner_2014_planetary`, Table 8.
    """

    mu: float = 3.79405852e7
    radius: float = 60268.0
    mass: float = 5.685e26

    @staticmethod
    def getPosition(jd: float) -> ndarray:
        """Calculate the ECI/J2000 position of Saturn's center at an epoch relative to the Earth.

        Args:
            jd (``float`` | ``Iterable``): :math:`N` epoch(s) at which the position is to be calculated (Julian date).

        Returns:
            ``ndarray``: 3x1 | Nx3 ECI position vector(s) of Saturn, where :math:`N` is the
            number of ``jd`` values entered (km).
        """
        # SS BC to Saturn center - SS BC to Earth BC - Earth BC to Earth Center
        position = getSegmentPosition(jd, TBK.SS_BC_2_SATURN_BC)
        position -= getSegmentPosition(jd, TBK.SS_BC_2_EARTH_BC)
        position -= getSegmentPosition(jd, TBK.EARTH_BC_2_EARTH_CENTER)
        return position


class Venus(ThirdBody):
    r"""Venus third body class.

    Attributes:
        mu (``float``): gravitational parameter, (km^3/sec^2), from DE430.
        radius (``float``): mean equatorial radius (km), from Vallado.
        mass (``float``): planet's mass (kg), from Vallado.

    References:
        :cite:t:`vallado_2013_astro`, Appendix D.3, Table D-3.
        :cite:t:`folkner_2014_planetary`, Table 8.
    """

    mu: float = 3.24858592e5
    radius: float = 6052.0
    mass: float = 4.869e24

    @staticmethod
    def getPosition(jd: float) -> ndarray:
        """Calculate the ECI/J2000 position of Venus's center at an epoch relative to the Earth.

        Args:
            jd (``float`` | ``Iterable``): :math:`N` epoch(s) at which the position is to be calculated (Julian date).

        Returns:
            ``ndarray``: 3x1 | Nx3 ECI position vector(s) of Venus, where :math:`N` is the
            number of ``jd`` values entered (km).
        """
        # SS BC to Venus center - SS BC to Earth BC - Earth BC to Earth Center
        position = getSegmentPosition(jd, TBK.SS_BC_2_VENUS_BC)
        position -= getSegmentPosition(jd, TBK.SS_BC_2_EARTH_BC)
        position -= getSegmentPosition(jd, TBK.EARTH_BC_2_EARTH_CENTER)
        return position
