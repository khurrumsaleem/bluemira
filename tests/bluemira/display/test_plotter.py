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
Tests for the plotter module.
"""

import numpy as np

from bluemira.base.components import GroupingComponent, PhysicalComponent
import bluemira.geometry as geo

from bluemira.display import plotter

SQUARE_POINTS = np.array(
    [
        (0.0, 0.0, 0.0),
        (1.0, 0.0, 0.0),
        (1.0, 0.0, 1.0),
        (0.0, 0.0, 1.0),
    ]
)


class TestPlotOptions:
    def test_default_options(self):
        """
        Check the values of the default options correspond to the global defaults.
        """
        the_options = plotter.PlotOptions()
        assert the_options.as_dict() == plotter.DEFAULT_PLOT_OPTIONS
        assert the_options.as_dict() is not plotter.DEFAULT_PLOT_OPTIONS

    def test_options(self):
        """
        Check the values can be set by passing kwargs.
        """
        the_options = plotter.PlotOptions(show_points=True)
        options_dict = the_options.as_dict()
        for key, val in options_dict.items():
            if key == "show_points":
                assert val != plotter.DEFAULT_PLOT_OPTIONS[key]
            else:
                assert val == plotter.DEFAULT_PLOT_OPTIONS[key]

    def test_options_plane_dict(self):
        """
        Check the options can be obtained as a dictionary with a BluemiraPlane
        """
        the_plane = geo.plane.BluemiraPlane()
        the_options = plotter.PlotOptions(plane=the_plane)
        options_dict = the_options.as_dict()
        for key, val in options_dict.items():
            if key == "plane":
                assert val != plotter.DEFAULT_PLOT_OPTIONS[key]
                assert val is not the_plane
            else:
                assert val == plotter.DEFAULT_PLOT_OPTIONS[key]

    def test_modify_options(self):
        """
        Check the display options can be modified by passing in keyword args
        """
        the_options = plotter.PlotOptions()
        the_options.modify(show_points=True)
        options_dict = the_options.as_dict()
        for key, val in options_dict.items():
            if key == "show_points":
                assert val != plotter.DEFAULT_PLOT_OPTIONS[key]
            else:
                assert val == plotter.DEFAULT_PLOT_OPTIONS[key]

    def test_properties(self):
        """
        Check the display option properties can be accessed
        """
        the_options = plotter.PlotOptions()
        for key, val in plotter.DEFAULT_PLOT_OPTIONS.items():
            assert getattr(the_options, key) == val

        the_options.show_points = not plotter.DEFAULT_PLOT_OPTIONS["show_points"]
        the_options.show_wires = not plotter.DEFAULT_PLOT_OPTIONS["show_wires"]
        the_options.show_faces = not plotter.DEFAULT_PLOT_OPTIONS["show_faces"]
        the_options.point_options = {}
        the_options.wire_options = {}
        the_options.face_options = {}
        the_options.plane = "xy"
        the_options.plane = geo.plane.BluemiraPlane()
        the_options.ndiscr = 20
        the_options.byedges = not plotter.DEFAULT_PLOT_OPTIONS["byedges"]

        for key, val in plotter.DEFAULT_PLOT_OPTIONS.items():
            assert getattr(the_options, key) != val


class TestPointsPlotter:
    def test_plotting_2d(self):
        plotter.PointsPlotter().plot_2d(SQUARE_POINTS)

    def test_plotting_3d(self):
        plotter.PointsPlotter().plot_3d(SQUARE_POINTS)


class TestWirePlotter:
    def setup_method(self):
        self.wire = geo.tools.make_polygon(SQUARE_POINTS)

    def test_plotting_2d(self):
        plotter.WirePlotter().plot_2d(self.wire)

    def test_plotting_2d_with_points(self):
        plotter.WirePlotter(show_points=True).plot_2d(self.wire)

    def test_plotting_3d(self):
        plotter.WirePlotter().plot_3d(self.wire)

    def test_plotting_3d_with_points(self):
        plotter.WirePlotter(show_points=True).plot_3d(self.wire)


class TestFacePlotter:
    def setup_method(self):
        wire = geo.tools.make_polygon(SQUARE_POINTS)
        wire.close()
        self.face = geo.face.BluemiraFace(wire)

    def test_plotting_2d(self):
        plotter.FacePlotter().plot_2d(self.face)

    def test_plotting_2d_with_wire(self):
        plotter.FacePlotter(show_wires=True).plot_2d(self.face)

    def test_plotting_3d(self):
        plotter.FacePlotter().plot_3d(self.face)

    def test_plotting_3d_with_wire_and_points(self):
        plotter.FacePlotter(show_wires=True, show_points=True).plot_3d(self.face)


class TestComponentPlotter:
    def setup_method(self):
        wire1 = geo.tools.make_polygon(SQUARE_POINTS, closed=True)
        wire2 = geo.tools.make_polygon(SQUARE_POINTS + 2.0, closed=True)
        face1 = geo.face.BluemiraFace(wire1)
        face2 = geo.face.BluemiraFace(wire2)

        self.group = GroupingComponent("Parent")
        self.child1 = PhysicalComponent("Child1", shape=face1, parent=self.group)
        self.child2 = PhysicalComponent("Child2", shape=face2, parent=self.group)

    def test_plotting_2d(self):
        plotter.ComponentPlotter().plot_2d(self.group)

    def test_plotting_2d_no_wires(self):
        plotter.ComponentPlotter(show_wires=True).plot_2d(self.group)

    def test_plotting_3d(self):
        plotter.ComponentPlotter().plot_3d(self.group)

    def test_plotting_3d_with_wires_and_points(self):
        plotter.ComponentPlotter(show_wires=True, show_points=True).plot_3d(self.group)
