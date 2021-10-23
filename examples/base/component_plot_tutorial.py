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
An example of how to use Components to represent a set of objects in a reactor.
"""

from anytree import RenderTree
import bluemira.base as bm_base

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

c = bm_base.PhysicalComponent("Comp", face)
c.plot()