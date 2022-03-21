# bluemira is an integrated inter-disciplinary design tool for future fusion
# reactors. It incorporates several modules, some of which rely on other
# codes, to carry out a range of typical conceptual fusion reactor design
# activities.
#
# Copyright (C) 2021 M. Coleman, J. Cook, F. Franza, I.A. Maione, S. McIntosh, J. Morris,
#                    D. Short
#
# bluemira is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# bluemira is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with bluemira; if not, see <https://www.gnu.org/licenses/>.

"""
Wrapper for FreeCAD Plane objects
"""

from __future__ import annotations

import copy

import numpy as np

import bluemira.codes._freecadapi as cadapi
from bluemira.geometry.constants import VERY_BIG
from bluemira.geometry.face import BluemiraFace

__all__ = ["BluemiraPlane"]


class BluemiraPlane:
    """
    Bluemira Plane class.

    Parameters
    ----------
    base: Iterable
        Plane reference point
    axis: Iterable
        normal vector dto the plane
    label: str
        Label of the plane
    """

    def __init__(self, base=(0.0, 0.0, 0.0), axis=(0.0, 0.0, 1.0), label: str = ""):
        if np.allclose(np.array(axis), np.array([0, 0, 0])):
            raise ValueError("Axis must to be a vector with non zero norm.")
        self._shape = cadapi.make_plane(base, axis)
        self.label = label

    @classmethod
    def from_3_points(cls, point_1, point_2, point_3, label: str = ""):
        """
        Instantiate a BluemiraPlane from three points.

        Parameters
        ----------
        point_1: Iterable
            First point
        point_2: Iterable
            Second Point
        point_3: Iterable
            Third point
        label: str
            Label of the plane
        """
        plane = BluemiraPlane()
        plane._shape = cadapi.make_plane_from_3_points(point_1, point_2, point_3)
        plane.label = label
        return plane

    @property
    def base(self):
        """Plane's reference point"""
        return cadapi.vector_to_numpy(self._shape.Position)

    @base.setter
    def base(self, value):
        """
        Set a new plane base

        Parameters
        ----------
        value: Iterable
        """
        self._shape.Position = cadapi.Base.Vector(value)

    @property
    def axis(self):
        """Plane's normal vector"""
        return cadapi.vector_to_numpy(self._shape.Axis)

    @axis.setter
    def axis(self, value):
        """
        Set a new plane axis

        Parameters
        ----------
        value: Iterable
        """
        self._shape.Axis = cadapi.Base.Vector(value)

    def move(self, vector):
        """Moves the Plane along the given vector"""
        self.base = self.base + np.array(vector)

    def __repr__(self):
        """
        Plane __repr__
        """
        return (
            f"([{type(self).__name__}] = Label: {self.label},"
            f" base: {self.base},"
            f" axis: {self.axis})"
        )

    def copy(self, label=None):
        """
        Make a copy of the BluemiraGeo.
        """
        plane_copy = copy.copy(self)
        if label is not None:
            plane_copy.label = label
        else:
            plane_copy.label = self.label
        return plane_copy

    def deepcopy(self, label=None):
        """Make a deepcopy of the BluemiraPlane"""
        plane_copy = BluemiraPlane(self.base, self.axis)
        if label is not None:
            plane_copy.label = label
        else:
            plane_copy.label = self.label
        return plane_copy

    def to_face(
        self, width: float = VERY_BIG, height: float = VERY_BIG, label: str = ""
    ):
        """
        Convert the plane to a face with dimension (width, height) and centered into
        the plane base position.
        """
        face = cadapi.face_from_plane(self._shape, width, height)
        bmface = BluemiraFace._create(face, label)
        return bmface

    def to_placement(self):
        """
        Convert the plane into a placement
        """
        from bluemira.geometry.placement import BluemiraPlacement

        return BluemiraPlacement._create(cadapi.placement_from_plane(self._shape))
