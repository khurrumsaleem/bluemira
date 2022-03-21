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
Wrapper for FreeCAD Placement objects
"""

from __future__ import annotations

import numpy as np

import bluemira.codes._freecadapi as cadapi
from bluemira.geometry.error import GeometryError
from bluemira.geometry.plane import BluemiraPlane

__all__ = ["BluemiraPlacement"]


class BluemiraPlacement:
    """
    Bluemira Placement class.

    Parameters
    ----------
    base: Iterable
        Placement origin
    axis: Iterable
        vector describing the axis of rotation
    angle: float
        angle of rotation in degree
    label: str
        Label of the placement
    """

    def __init__(
        self, base=[0.0, 0.0, 0.0], axis=[0.0, 0.0, 1.0], angle=0.0, label: str = ""
    ):
        self._shape = cadapi.make_placement(base, axis, angle)
        self.label = label

    @classmethod
    def from_3_points(cls, point_1, point_2, point_3, label: str = ""):
        """
        Instantiate a BluemiraPlacement from three points.

        Parameters
        ----------
        point_1: Iterable
            First point
        point_2: Iterable
            Second Point
        point_3: Iterable
            Third point
        label: str
            Label of the placement
        """
        p1 = np.array(point_1)
        p2 = np.array(point_2)
        p3 = np.array(point_3)
        v1, v2 = p3 - p1, p2 - p1
        v3 = np.cross(v2, v1)
        if np.all(v3 == 0):
            raise GeometryError("Cannot make a BluemiraPlacement from co-linear points.")

        normal = v3 / np.sqrt(v3.dot(v3))
        return cls(point_1, normal, 0.0, label=label)

    @classmethod
    def from_matrix(cls, matrix, label=""):
        """
        Instantiate a BluemiraPlacement from a 4 x 4 matrix

        Parameters
        ----------
        matrix: np.ndarray
            4 x 4 matrix from which to make the placement
        label: str
            Label of the placement
        """
        obj = cls.__new__(cls)
        obj._shape = cadapi.make_placement_from_matrix(matrix)
        obj.label = label
        return obj

    @property
    def base(self):
        """Placement's local origin"""
        return cadapi.vector_to_numpy(self._shape.Base)

    @base.setter
    def base(self, value):
        """
        Set a new placement base

        Parameters
        ----------
        value: Iterable
        """
        self._shape.Base = cadapi.Base.Vector(value)

    @property
    def axis(self):
        """Placement's rotation matrix"""
        return self._shape.Rotation.Axis

    @axis.setter
    def axis(self, value):
        """
        Set a new placement axis

        Parameters
        ----------
        value: Iterable
        """
        self._shape.Axis = cadapi.Base.Vector(value)

    @property
    def angle(self):
        """Placement's angle of rotation"""
        return np.rad2deg(self._shape.Rotation.Angle)

    @angle.setter
    def angle(self, value):
        """
        Set a new placement angle of rotation

        Parameters
        ----------
        value: float
            angle value in degree
        """
        self._shape.Angle = value

    def to_matrix(self):
        """Returns a matrix (quaternion) representing the Plascement's transformation"""
        return np.array(self._shape.Matrix.A).reshape(4, 4)

    def inverse(self):
        """Returns the inverse placement"""
        return BluemiraPlacement._create(
            self._shape.inverse(), label=self.label + "_inverse"
        )

    def move(self, vector):
        """Moves the Placement along the given vector"""
        cadapi.move_placement(self._shape, vector)

    def __repr__(self):  # noqa D105
        new = []
        new.append(f"([{type(self).__name__}] = Label: {self.label}")
        new.append(f" base: {self.base}")
        new.append(f" axis: {self.axis}")
        new.append(f" angle: {self.angle}")
        new.append(")")
        return ", ".join(new)

    def copy(self, label=None):
        """Make a copy of the BluemiraPlacement"""
        placement_copy = BluemiraPlacement(self.base, self.axis, self.angle)
        if label is not None:
            placement_copy.label = label
        else:
            placement_copy.label = self.label
        return placement_copy

    def deepcopy(self, label=None):
        """Make a deepcopy of the BluemiraPlacement"""
        return self.copy()

    @classmethod
    def _create(cls, obj: cadapi.apiPlacement, label="") -> BluemiraPlacement:
        """Create a placement from a cadapi Placement"""
        if isinstance(obj, cadapi.apiPlacement):
            placement = BluemiraPlacement(label=label)
            placement._shape = obj
            return placement

        raise TypeError(
            f"Only Base.Placement objects can be used to create a {cls} instance"
        )

    def mult_vec(self, vec):
        """Transform a vector into the local placement"""
        return cadapi.vector_to_numpy(self._shape.multVec(cadapi.Base.Vector(vec)))

    def extract_plane(self, v1, v2, base=None):
        """
        Return a plane identified by two vector given in the self placement

        Parameters
        ----------
        v1: Iterable
            first reference vector
        v2: Iterable
            second reference vector
        base: float
            output plane origin

        Returns
        -------
        plane: BluemiraPlane
        """
        if base is None:
            base = self.base

        p1 = self.mult_vec(v1)
        p2 = self.mult_vec(v2)

        return BluemiraPlane.from_3_points(base, p1, p2)

    def xy_plane(self):
        """Returns the corresponding placement xy plane"""
        return self.extract_plane(v1=np.array([1, 0, 0]), v2=np.array([0, 1, 0]))

    def yz_plane(self):
        """Returns the corresponding placement yz plane"""
        return self.extract_plane(v1=np.array([0, 1, 0]), v2=np.array([0, 0, 1]))

    def xz_plane(self):
        """Returns the corresponding placement xz plane"""
        return self.extract_plane(v1=np.array([1, 0, 0]), v2=np.array([0, 0, 1]))


XYZ = BluemiraPlacement(label="xyz")
YZX = BluemiraPlacement.from_matrix(
    matrix=np.array([[0, 0, 1, 0], [1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 0, 1]]),
    label="yzx",
)
XZY = BluemiraPlacement(axis=(1.0, 0.0, 0.0), angle=-90.0, label="xzy")
