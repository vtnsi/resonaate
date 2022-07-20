from __future__ import annotations

# Third Party Imports
import pytest
from numpy import allclose, array, ndarray

# RESONAATE Imports
from resonaate.physics.bodies import Jupiter, Moon, Saturn, Sun
from resonaate.physics.bodies.third_body import (
    TBK,
    ThirdBodyTuple,
    Venus,
    getSegmentPosition,
    loadKernelData,
    readKernelSegmentFile,
    readKernelSegments,
)
from resonaate.physics.time.stardate import JulianDate

# Julian dates at which each TB test compares vs. jplephem
JULIAN_DATES = [
    2458527.5,
    2459232.68076,
    2459263.68076,
    2459291.0,
    2459322.68076,
    2455335.0141,
    2455365.7641,
    2455426.7641,
]

# True values obtained directly using `jplephem` library
JPL_EPHEM_SUN = (
    array([119057220.54450887, -80174634.82332915, -34756419.36076262]),
    array([69107469.62028551, -119226928.52795392, -51685226.907349035]),
    array([127323469.06143504, -68962101.4390411, -29895543.306474928]),
    array([148638656.02918416, -7557862.752354181, -3277031.6466259]),
    array([132537374.04737763, 64861458.58805199, 28116997.50547948]),
    array([81708251.47452828, 116858603.72575748, 50660750.16189619]),
    array([8519833.168042015, 139233775.69597003, 60360902.23895398]),
    array([-124157587.19967724, 79542210.82395323, 34483802.41564018]),
)

JPL_EPHEM_MOON = (
    array([222662.48906104316, 298651.50080616487, 95734.93247350478]),
    array([395448.65612840565, 3121.7648710382423, -37191.93559130262]),
    array([299594.6832387903, 256594.62049760265, 89237.8142898709]),
    array([300113.2416606487, 256298.80579109892, 90875.49826567038]),
    array([-29014.763446231682, 360721.11435647914, 171824.73029669753]),
    array([-154816.24181181786, 311744.510628804, 127505.47381284401]),
    array([-354687.3067773787, 101853.82313577276, 11286.30946979568]),
    array([-112812.30993091817, -335328.80197536974, -163309.90792258029]),
)

JPL_EPHEM_JUPITER = (
    array([-155715610.5536356, -771593805.7306125, -324428864.4725702]),
    array([539297868.5558921, -665489073.6328514, -297273671.7757187]),
    array([624128539.8741837, -592997575.71752, -266604867.19497398]),
    array([668006315.0242654, -511061356.7869685, -231734985.3395112]),
    array([676964535.9973992, -413765730.71923727, -190288252.67939237]),
    array([806002626.1406696, -33412690.309808254, -31384344.70350618]),
    array([739517604.8260012, 21790852.268733684, -7776186.843133321]),
    array([615188522.563155, 27942634.375971355, -5634155.066650251]),
)

JPL_EPHEM_SATURN = (
    array([445396551.3256828, -1432794618.013808, -607517595.3682841]),
    array([901614201.6406103, -1252345965.7070923, -555567076.2057778]),
    array([979781207.6109266, -1188308041.3472142, -528947069.0378752]),
    array([1018474985.2245942, -1114498293.505165, -497952393.4926775]),
    array([1022282198.9192564, -1027382208.8899746, -461344661.3236429]),
    array([-1338736304.3277442, 23968326.74098009, 73458680.87779231]),
    array([-1411693618.7646015, 22644453.396800224, 73360820.51010266]),
    array([-1542556939.865906, -83939701.05154786, 28038186.979149718]),
)

JPL_EPHEM_VENUS = (
    array([25248376.503555316, -131046502.4236743, -51710581.63809083]),
    array([48866906.98203094, -217050363.9265716, -94420541.75883316]),
    array([194790102.5546299, -145288277.92984402, -68507522.52351148]),
    array([256053997.05789733, -19569878.97916062, -15478251.584634146]),
    array([212762052.9621936, 132837318.34650537, 53627045.34750387]),
    array([7054919.128941293, 185486556.69872993, 86261718.69691297]),
    array([-98803182.93923302, 129945435.41415145, 62973077.689478755]),
    array([-102597689.75835262, -17234608.62430422, -10422288.934953073]),
)

# Combined Julian dates and ephemeris to check against
SUN_POSITIONS = list(zip(JULIAN_DATES, JPL_EPHEM_SUN))
MOON_POSITIONS = list(zip(JULIAN_DATES, JPL_EPHEM_MOON))
JUPITER_POSITIONS = list(zip(JULIAN_DATES, JPL_EPHEM_JUPITER))
SATURN_POSITIONS = list(zip(JULIAN_DATES, JPL_EPHEM_SATURN))
VENUS_POSITIONS = list(zip(JULIAN_DATES, JPL_EPHEM_VENUS))

KERNEL_FILES = [
    # (filename, is_valid)
    ("0-1-2433264.5-8.0.npy", True),
    ("0-2-2433264.5-16.0.npy", True),
    ("0-3-2433264.5-16.0.npy", True),
    ("0-4-2433264.5-32.0.npy", True),
    ("0-5-2433264.5-32.0.npy", True),
    ("0-6-2433264.5-32.0.npy", True),
    ("0-7-2433264.5-32.0.npy", True),
    ("0-8-2433264.5-32.0.npy", True),
    ("0-9-2433264.5-32.0.npy", True),
    ("0-10-2433264.5-16.0.npy", True),
    ("1-199-2433264.5-36544.0.npy", True),
    ("2-299-2433264.5-36544.0.npy", True),
    ("3-301-2433264.5-4.0.npy", True),
    ("3-399-2433264.5-4.0.npy", True),
    ("1-2-2433264.5-16.0.npy", False),
]

KERNELS = [
    # (kernel, is_valid)
    ("de432s", True),
    ("de420", False),
]

SEGMENTS = [
    # Segment
    TBK.SS_BC_2_MERCURY_BC,
    TBK.SS_BC_2_VENUS_BC,
    TBK.SS_BC_2_EARTH_BC,
    TBK.SS_BC_2_MARS_BC,
    TBK.SS_BC_2_JUPITER_BC,
    TBK.SS_BC_2_SATURN_BC,
    TBK.SS_BC_2_URANUS_BC,
    TBK.SS_BC_2_NEPTUNE_BC,
    TBK.SS_BC_2_PLUTO_BC,
    TBK.SS_BC_2_SUN_CENTER,
    TBK.EARTH_BC_2_MOON_CENTER,
    TBK.EARTH_BC_2_EARTH_CENTER,
    TBK.MERCURY_BC_2_MERCURY_CENTER,
    TBK.VENUS_BC_2_VENUS_CENTER,
]


@pytest.mark.parametrize(("julian_date", "true_position"), SUN_POSITIONS)
def testSunSingleJD(julian_date: JulianDate, true_position: ndarray):
    """Test accuracy of single Julian date inputs for Sun position."""
    jd = JulianDate(julian_date)
    sun_position = Sun.getPosition(jd)

    # Test assertions
    assert isinstance(sun_position, ndarray)
    assert sun_position.shape == (3,)
    assert allclose(true_position, sun_position, rtol=1e-8, atol=1e-12)


def testSunMultipleJD():
    """Test accuracy of multiple Julian dates inputs for Sun position."""
    sun_positions = Sun.getPosition(JULIAN_DATES)

    # Test assertions
    assert isinstance(sun_positions, ndarray)
    assert sun_positions.shape == (len(JULIAN_DATES), 3)
    assert allclose(sun_positions, JPL_EPHEM_SUN, rtol=1e-8, atol=1e-12)


@pytest.mark.parametrize(("julian_date", "true_position"), MOON_POSITIONS)
def testMoonSingleJD(julian_date: JulianDate, true_position: ndarray):
    """Test accuracy of single Julian date inputs for Moon position."""
    jd = JulianDate(julian_date)
    moon_position = Moon.getPosition(jd)

    # Test assertions
    assert isinstance(moon_position, ndarray)
    assert moon_position.shape == (3,)
    assert allclose(true_position, moon_position, rtol=1e-8, atol=1e-12)


def testMoonMultipleJD():
    """Test accuracy of multiple Julian dates inputs for Moon position."""
    moon_positions = Moon.getPosition(JULIAN_DATES)

    # Test assertions
    assert isinstance(moon_positions, ndarray)
    assert moon_positions.shape == (len(JULIAN_DATES), 3)
    assert allclose(moon_positions, JPL_EPHEM_MOON, rtol=1e-8, atol=1e-12)


@pytest.mark.parametrize(("julian_date", "true_position"), JUPITER_POSITIONS)
def testJupiterSingleJD(julian_date: JulianDate, true_position: ndarray):
    """Test accuracy of single Julian date inputs for Jupiter position."""
    jd = JulianDate(julian_date)
    jupiter_position = Jupiter.getPosition(jd)

    # Test assertions
    assert isinstance(jupiter_position, ndarray)
    assert jupiter_position.shape == (3,)
    assert allclose(true_position, jupiter_position, rtol=1e-8, atol=1e-12)


def testJupiterMultipleJD():
    """Test accuracy of multiple Julian dates inputs for Jupiter position."""
    jupiter_positions = Jupiter.getPosition(JULIAN_DATES)

    # Test assertions
    assert isinstance(jupiter_positions, ndarray)
    assert jupiter_positions.shape == (len(JULIAN_DATES), 3)
    assert allclose(jupiter_positions, JPL_EPHEM_JUPITER, rtol=1e-8, atol=1e-12)


@pytest.mark.parametrize(("julian_date", "true_position"), SATURN_POSITIONS)
def testSaturnSingleJD(julian_date: JulianDate, true_position: ndarray):
    """Test accuracy of single Julian date inputs for Saturn position."""
    jd = JulianDate(julian_date)
    saturn_position = Saturn.getPosition(jd)

    # Test assertions
    assert isinstance(saturn_position, ndarray)
    assert saturn_position.shape == (3,)
    assert allclose(true_position, saturn_position, rtol=1e-8, atol=1e-12)


def testSaturnMultipleJD():
    """Test accuracy of multiple Julian dates inputs for Saturn position."""
    saturn_positions = Saturn.getPosition(JULIAN_DATES)

    # Test assertions
    assert isinstance(saturn_positions, ndarray)
    assert saturn_positions.shape == (len(JULIAN_DATES), 3)
    assert allclose(saturn_positions, JPL_EPHEM_SATURN, rtol=1e-8, atol=1e-12)


@pytest.mark.parametrize(("julian_date", "true_position"), VENUS_POSITIONS)
def testVenusSingleJD(julian_date: JulianDate, true_position: ndarray):
    """Test accuracy of single Julian date inputs for Venus position."""
    jd = JulianDate(julian_date)
    venus_position = Venus.getPosition(jd)

    # Test assertions
    assert isinstance(venus_position, ndarray)
    assert venus_position.shape == (3,)
    assert allclose(true_position, venus_position, rtol=1e-8, atol=1e-12)


def testVenusMultipleJD():
    """Test accuracy of multiple Julian dates inputs for Saturn position."""
    venus_positions = Venus.getPosition(JULIAN_DATES)

    # Test assertions
    assert isinstance(venus_positions, ndarray)
    assert venus_positions.shape == (len(JULIAN_DATES), 3)
    assert allclose(venus_positions, JPL_EPHEM_VENUS, rtol=1e-8, atol=1e-12)


@pytest.mark.parametrize(("filename", "is_valid"), KERNEL_FILES)
def testReadKernelSegmentFile(filename: str, is_valid: bool):
    """Test reading single kernel segment files directly."""
    kernel_module = f"resonaate.physics.data.{KERNELS[0][0]}"
    if is_valid:
        tb_tuple = readKernelSegmentFile(kernel_module, filename)
        assert isinstance(tb_tuple, ThirdBodyTuple)

    else:
        with pytest.raises(FileNotFoundError):
            readKernelSegmentFile(kernel_module, filename)


@pytest.mark.parametrize(("directory", "is_valid"), KERNELS)
def testReadKernelSegments(directory: str, is_valid: bool):
    """Test reading kernel directories."""
    kernel_module = f"resonaate.physics.data.{directory}"
    if is_valid:
        tb_tuples = readKernelSegments(kernel_module)
        assert isinstance(tb_tuples, list)
        for tb_tuple in tb_tuples:
            assert isinstance(tb_tuple, ThirdBodyTuple)

    else:
        with pytest.raises(ModuleNotFoundError):
            readKernelSegments(kernel_module)


@pytest.mark.parametrize(("kernel", "is_valid"), KERNELS)
def testLoadingKernel(kernel: str, is_valid: bool):
    """Test loading kernels in the resonaate library."""
    if is_valid:
        tb_tuples = loadKernelData(kernel)
        assert isinstance(tb_tuples, tuple)
        for tb_tuple in tb_tuples:
            assert isinstance(tb_tuple, tuple)
            assert len(tb_tuple) == 3
            assert isinstance(tb_tuple[0], float)
            assert isinstance(tb_tuple[1], float)
            assert isinstance(tb_tuple[2], ndarray)

    else:
        with pytest.raises(ModuleNotFoundError):
            loadKernelData(kernel)


@pytest.mark.parametrize("segment", SEGMENTS)
def testSegmentPosition(segment: TBK):
    """Test calculating positions for all segments."""
    position = getSegmentPosition(2458527.5, segment)
    assert isinstance(position, ndarray)
    assert position.shape == (3,)
