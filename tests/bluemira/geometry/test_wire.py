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
import numpy as np
import pytest

from bluemira.geometry.coordinates import Coordinates
from bluemira.geometry.error import GeometryError
from bluemira.geometry.tools import make_bezier, make_circle, make_polygon
from bluemira.geometry.wire import BluemiraWire


class TestWire:
    def test_start_point_given_polygon(self):
        n_coords = 10
        coords = np.zeros((3, n_coords))
        coords[0, :] = np.linspace(0, 2, n_coords)
        coords[2, :] = np.linspace(-5, 0, n_coords)
        wire = make_polygon(coords)

        start_point = wire.start_point()

        assert isinstance(start_point, Coordinates)
        np.testing.assert_equal(start_point, np.array([[0], [0], [-5]]))

    def test_end_point_given_polygon(self):
        n_coords = 10
        coords = np.zeros((3, n_coords))
        coords[0, :] = np.linspace(0, 2, n_coords)
        coords[2, :] = np.linspace(-5, 0, n_coords)
        wire = make_polygon(coords)

        end_point = wire.end_point()

        assert isinstance(end_point, Coordinates)
        np.testing.assert_equal(end_point, np.array([[2], [0], [0]]))

    def test_start_point_eq_end_point_given_circle(self):
        wire = make_circle(radius=2, center=(0, 0, 0))

        start_point = wire.start_point()
        end_point = wire.end_point()

        assert start_point == end_point

    def test_start_point_given_bezier(self):
        n_coords = 11
        coords = np.zeros((3, n_coords))
        coords[0, :] = np.linspace(-5, 5, n_coords)
        coords[1, :] = np.linspace(0.1, 0.2, n_coords)
        coords[2, :] = np.linspace(100, 90, n_coords)
        wire = make_bezier(coords)

        start_point = wire.start_point()

        np.testing.assert_equal(start_point, np.array([[-5], [0.1], [100]]))

    def test_end_point_given_bezier(self):
        n_coords = 11
        coords = np.zeros((3, n_coords))
        coords[0, :] = np.linspace(-5, 5, n_coords)
        coords[1, :] = np.linspace(0.1, 0.2, n_coords)
        coords[2, :] = np.linspace(100, 90, n_coords)
        wire = make_bezier(coords)

        start_point = wire.end_point()

        np.testing.assert_equal(start_point, np.array([[5], [0.2], [90]]))


class TestWireValueAt:
    @classmethod
    def setup_class(cls):
        cls.square = make_polygon(
            {"x": [0, 2, 2, 0], "y": 0, "z": [0, 0, 2, 2]}, closed=True
        )
        line = make_polygon([[0, 0, 0], [1, 0, 0]])
        semicircle = make_circle(
            1, center=(1, 0, -1), start_angle=90, end_angle=270, axis=(0, -1, 0)
        )
        line2 = make_polygon([[1, 0, -2], [2, 0, -2]])
        cls.mixed = BluemiraWire([line, semicircle, line2])

    @pytest.mark.parametrize(
        "alpha, expected_point",
        [
            (0, [0, 0, 0]),
            (0.25, [2, 0, 0]),
            (0.375, [2, 0, 1]),
            (0.5, [2, 0, 2]),
            ([0.75, [0, 0, 2]]),
            ([1.0, [0, 0, 0]]),
            ([1.1, [0, 0, 0]]),
            ([-1.0, [0, 0, 0]]),
        ],
    )
    def test_square_alpha(self, alpha, expected_point):
        np.testing.assert_allclose(
            self.square.value_at(alpha=alpha), np.array(expected_point)
        )

    @pytest.mark.parametrize(
        "l_frac, expected_point",
        [
            (0, [0, 0, 0]),
            (0.25, [2, 0, 0]),
            (0.375, [2, 0, 1]),
            (0.5, [2, 0, 2]),
            ([0.75, [0, 0, 2]]),
            ([1.0, [0, 0, 0]]),
            ([1.1, [0, 0, 0]]),
            ([-1.0, [0, 0, 0]]),
        ],
    )
    def test_square_distance(self, l_frac, expected_point):
        length = self.square.length
        np.testing.assert_allclose(
            self.square.value_at(distance=l_frac * length), np.array(expected_point)
        )

    def test_mixed_alpha(self):
        assert np.allclose(self.mixed.value_at(alpha=0.0), np.array([0, 0, 0]))
        assert np.allclose(self.mixed.value_at(alpha=0.5), np.array([0, 0, -1]))
        assert np.allclose(self.mixed.value_at(alpha=1.0), np.array([2, 0, -2]))

    def test_mixed_distance(self):
        length = self.mixed.length
        assert np.allclose(self.mixed.value_at(distance=0.0), np.array([0, 0, 0]))
        assert np.allclose(
            self.mixed.value_at(distance=0.5 * length), np.array([0, 0, -1])
        )
        assert np.allclose(self.mixed.value_at(distance=length), np.array([2, 0, -2]))

    def test_point_along_wire_at_length_2d(self):
        # Line in 2d: z = 3x - 4
        coords = np.array([[1, 2, 3, 4, 5], [0, 0, 0, 0, 0], [-1, 2, 5, 8, 11]])
        wire = make_polygon(coords)
        desired_len = np.sqrt(2.5)
        point = wire.value_at(distance=desired_len)

        np.testing.assert_almost_equal(point, [1.5, 0, 0.5], decimal=2)

    def test_point_along_wire_at_length_3d(self):
        circle = make_circle(radius=1, axis=[1, 1, 1])
        semi_circle = make_circle(radius=1, axis=[1, 1, 1], end_angle=180)

        point = circle.value_at(distance=np.pi)

        np.testing.assert_almost_equal(point, semi_circle.end_point().T[0], decimal=2)

    def test_two_value_error(self):
        line = make_polygon([[0, 0, 0], [1, 0, 0]])
        with pytest.raises(GeometryError):
            line.value_at(alpha=0.5, distance=0.5)

    def test_no_value_error(self):
        line = make_polygon([[0, 0, 0], [1, 0, 0]])
        with pytest.raises(GeometryError):
            line.value_at()
