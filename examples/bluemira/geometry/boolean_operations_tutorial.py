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
Boolean operations examples
"""

import bluemira.geometry as geometry
import freecad
import Part

from bluemira.plotting.plotter import (
    PointsPlotter,
    WirePlotter,
    FacePlotter,
    FaceCompoundPlotter,
)
from bluemira.geometry.parameterisations import PrincetonD
from bluemira.geometry.face import BluemiraFace

# creation of a closed wire and respective face
# PrincetonD parametrization is used as example.
# Note: the curve is generated into the xz plane
p = PrincetonD()
p.adjust_variable("x1", 4, lower_bound=3, upper_bound=5)
p.adjust_variable("x2", 16, lower_bound=10, upper_bound=20)
p.adjust_variable("dz", 0, lower_bound=0, upper_bound=0)
wire = p.create_shape()
face = BluemiraFace(wire)

# a second geometry is created (it contains the first face)
p2 = PrincetonD()
p2.adjust_variable("x1", 3.5, lower_bound=3, upper_bound=5)
p2.adjust_variable("x2", 17, lower_bound=10, upper_bound=20)
p2.adjust_variable("dz", 0, lower_bound=0, upper_bound=0)
wire2 = p2.create_shape()
face2 = BluemiraFace(wire2)

# a third face is create as difference between face and face2 (a BluemiraFace object
# has been created using wire2 as outer boundary and wire as inner boundary
# Note:
# - face3 is created with a wire deepcopy in order to be able to modify face and face2
# (and thus wire and wire2) without modifying face3
face3 = BluemiraFace([wire2.deepcopy()])
# some operations on face
bari = face3.center_of_mass
face3.scale(0.5)
new_bari = face3.center_of_mass
diff = bari - new_bari
v = (diff[0], diff[1], diff[2])
face3.translate(v)


cut_face = face2._shape.cut(face._shape)
output = [BluemiraFace._create(f) for f in cut_face.Faces] + [face3]

# print(f"plot face with hole")
fplotter = FaceCompoundPlotter(plane="xz")
# fplotter(output, show=True, block=True, ndiscr=5, byedges=True)

wire = geometry.tools.make_polygon([[0,0,0], [20,0,0]])

import BOPTools.SplitAPI

compound = [BOPTools.SplitAPI.slice(o._shape, [wire._shape], "Split") for o in output]

output2 = [BluemiraFace._create(f) for c in compound for f in c.Faces]

print(f"plot bottom part of cut face")
fplotter.plot_points = False
fplotter(output2, show=True, block=True, ndiscr=50, byedges=True)

# another test
fc = face._shape
piece, map = fc.generalFuse([face2._shape])
