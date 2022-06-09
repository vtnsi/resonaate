# pylint: disable=attribute-defined-outside-init, no-self-use
# Standard Library Imports
import os
# Third Party Imports
import pytest
from numpy import array, ndarray, allclose
# RESONAATE Imports
try:
    from resonaate.physics.bodies import Moon, Sun
    from resonaate.physics.bodies.third_body import (
        readKernelSegmentFile, readKernelSegments, ThirdBodyTuple, loadKernelData, TBK, getSegmentPosition
    )
    from resonaate.physics.time.stardate import JulianDate
except ImportError as error:
    raise Exception(
        f"Please ensure you have appropriate packages installed:\n {error}"
    ) from error
# Testing Imports
from ..conftest import BaseTestCase
from .conftest import PHYSICS_DATA_DIR


class TestThirdBody(BaseTestCase):
    """Perform set of test on the Third Body module."""

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

    # Combined Julian dates and ephemeris to check against
    SUN_POSITIONS = list(zip(JULIAN_DATES, JPL_EPHEM_SUN))
    MOON_POSITIONS = list(zip(JULIAN_DATES, JPL_EPHEM_MOON))

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

    @pytest.mark.parametrize("julian_date, true_position", SUN_POSITIONS)
    def testSunSingleJD(self, julian_date, true_position):
        """Test accuracy of single Julian date inputs for Sun position."""
        jd = JulianDate(julian_date)
        sun_position = Sun.getPosition(jd)

        # Test assertions
        assert isinstance(sun_position, ndarray)
        assert sun_position.shape == (3, )
        assert allclose(true_position, sun_position, rtol=1e-8, atol=1e-12)

    def testSunMultipleJD(self):
        """Test accuracy of multiple Julian dates inputs for Sun position."""
        sun_positions = Sun.getPosition(self.JULIAN_DATES)

        # Test assertions
        assert isinstance(sun_positions, ndarray)
        assert sun_positions.shape == (len(self.JULIAN_DATES), 3)
        assert allclose(sun_positions, self.JPL_EPHEM_SUN, rtol=1e-8, atol=1e-12)

    @pytest.mark.parametrize("julian_date, true_position", MOON_POSITIONS)
    def testMoonSingleJD(self, julian_date, true_position):
        """Test accuracy of single Julian date inputs for Moon position."""
        jd = JulianDate(julian_date)
        moon_position = Moon.getPosition(jd)

        # Test assertions
        assert isinstance(moon_position, ndarray)
        assert moon_position.shape == (3, )
        assert allclose(true_position, moon_position, rtol=1e-8, atol=1e-12)

    def testMoonMultipleJD(self):
        """Test accuracy of multiple Julian dates inputs for Moon position."""
        moon_positions = Moon.getPosition(self.JULIAN_DATES)

        # Test assertions
        assert isinstance(moon_positions, ndarray)
        assert moon_positions.shape == (len(self.JULIAN_DATES), 3)
        assert allclose(moon_positions, self.JPL_EPHEM_MOON, rtol=1e-8, atol=1e-12)

    @pytest.mark.parametrize("filename, is_valid", KERNEL_FILES)
    @pytest.mark.datafiles(PHYSICS_DATA_DIR)
    def testReadKernelSegmentFile(self, datafiles, filename, is_valid):
        """Test reading single kernel segment files directly."""
        kernel_file = os.path.join(
            datafiles,
            self.KERNELS[0][0],
            filename
        )
        if is_valid:
            tb_tuple = readKernelSegmentFile(kernel_file)
            assert isinstance(tb_tuple, ThirdBodyTuple)

        else:
            with pytest.raises(FileNotFoundError):
                readKernelSegmentFile(kernel_file)

    @pytest.mark.parametrize("directory, is_valid", KERNELS)
    @pytest.mark.datafiles(PHYSICS_DATA_DIR)
    def testReadKernelSegments(self, datafiles, directory, is_valid):
        """Test reading kernel directories."""
        kernel_dir = os.path.join(
            datafiles,
            directory
        )
        if is_valid:
            tb_tuples = readKernelSegments(kernel_dir)
            assert isinstance(tb_tuples, list)
            for tb_tuple in tb_tuples:
                assert isinstance(tb_tuple, ThirdBodyTuple)

        else:
            with pytest.raises(FileNotFoundError):
                readKernelSegments(kernel_dir)

    @pytest.mark.parametrize("kernel, is_valid", KERNELS)
    def testLoadingKernel(self, kernel, is_valid):
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
            with pytest.raises(FileNotFoundError):
                loadKernelData(kernel)

    @pytest.mark.parametrize("segment", SEGMENTS)
    def testSegmentPosition(self, segment):
        """Test calculating positions for all segments."""
        position = getSegmentPosition(2458527.5, segment)
        assert isinstance(position, ndarray)
        assert position.shape == (3,)
