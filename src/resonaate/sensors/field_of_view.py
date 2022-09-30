"""Abstract :class:`.FieldOfView` base class and subclasses for field of view interface."""
from __future__ import annotations

# Standard Library Imports
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

# Local Imports
from ..physics.math import subtendedAngle
from .measurements import getAzimuth, getElevation

if TYPE_CHECKING:
    # Third Party Imports
    from numpy import ndarray


class FieldOfView(ABC):
    """Abstract base class describing a generic field of view of a sensor.

    Note:
        Must be overridden by a `FieldOfView` subclass
    """

    @abstractmethod
    def inFieldOfView(self, pointing_sez: ndarray, background_sez: ndarray) -> bool:
        """Determine whether `background_sez` state is within the field of view of the `pointing_sez` state.

        Args:
            pointing_sez (``ndarray``): 6x1 slant range vector that sensor is pointing towards [km; km/sec]
            background_sez (``ndarray``): 6x1 slant range vector of possible agent in FoV [km; km/sec]

        Returns:
            ``bool``: True if `background_sez` state is within field of view of current pointing state
        """
        raise NotImplementedError


class ConicFoV(FieldOfView):
    """Conic Field of View Subclass.

    Attributes:
        cone_angle (``float``): Diameter of sensor viewing cone (rad)
    """

    def __init__(self, cone_angle: float) -> None:
        """Initialize A ConicFoV object.

        Args:
            cone_angle (``float``): Diameter of sensor viewing cone (rad)
        """
        self._cone_angle = cone_angle

    def inFieldOfView(self, pointing_sez: ndarray, background_sez: ndarray) -> bool:
        """Determine whether `background_sez` state is within the field of view of the `pointing_sez` state.

        Args:
            pointing_sez (``ndarray``): 6x1 slant range vector that sensor is pointing towards [km; km/sec]
            background_sez (``ndarray``): 6x1 slant range vector of possible agent in FoV [km; km/sec]

        Returns:
            ``bool``: True if `background_sez` state is within field of view of current pointing state
        """
        angle = subtendedAngle(background_sez[:3], pointing_sez[:3])
        return angle <= self.cone_angle / 2

    @property
    def cone_angle(self) -> float:
        """``float``: Returns Cone angle of sensor."""
        return self._cone_angle


class RectangularFoV(FieldOfView):
    """Rectangular Field of View Subclass.

    Attributes:
        azimuth_angle (``float``): full azimuth span of sensor field of view (rad)
        elevation_angle (``float``): full elevation span of sensor field of view (rad)
    """

    def __init__(self, azimuth_angle: float, elevation_angle: float) -> None:
        """Initialize A RectangularFoV object.

        Args:
            azimuth_angle (``float``): full azimuth span of sensor field of view (rad)
            elevation_angle (``float``): full elevation span of sensor field of view (rad)
        """
        self._azimuth_angle = azimuth_angle
        self._elevation_angle = elevation_angle

    def inFieldOfView(self, pointing_sez: ndarray, background_sez: ndarray) -> bool:
        """Determine whether `background_sez` state is within the field of view of the `pointing_sez` state.

        Args:
            pointing_sez (``ndarray``): 6x1 slant range vector that sensor is pointing towards [km; km/sec]
            background_sez (``ndarray``): 6x1 slant range vector of possible agent in FoV [km; km/sec]

        Returns:
            ``bool``: True if `background_sez` state is within field of view of current pointing state
        """
        pointing_azimuth = getAzimuth(pointing_sez)
        pointing_elevation = getElevation(pointing_sez)

        background_azimuth = getAzimuth(background_sez)
        background_elevation = getElevation(background_sez)

        azimuth_angle = abs(pointing_azimuth - background_azimuth)
        elevation_angle = abs(pointing_elevation - background_elevation)
        return (
            azimuth_angle <= self.azimuth_angle / 2 and elevation_angle <= self.elevation_angle / 2
        )

    @property
    def azimuth_angle(self) -> float:
        """``float``: Returns azimuth angle of sensor."""
        return self._azimuth_angle

    @property
    def elevation_angle(self) -> float:
        """``float``: Returns elevation angle of sensor."""
        return self._elevation_angle
