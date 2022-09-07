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
Module containing builders for the EUDEMO first wall components
"""
from bluemira.base.designer import run_designer
from EUDEMO_builders.ivc.divertor_silhouette import DivertorSilhouetteDesigner
from EUDEMO_builders.ivc.ivc_boundary import IVCBoundaryDesigner
from EUDEMO_builders.ivc.plasma_face import PlasmaFaceDesigner
from EUDEMO_builders.ivc.wall_silhouette import WallSilhouetteDesigner
from EUDEMO_builders.ivc.wall_silhouette_parameterisation import (
    WallPolySpline,
    WallPrincetonD,
)


def design_ivc(params, build_config, equilibrium):
    """Run the IVC component designers in sequence."""
    wall_shape = run_designer(
        WallSilhouetteDesigner,
        params,
        build_config["Wall silhouette"],
        equilibrium=equilibrium,
    ).create_shape(label="wall")
    divertor_shapes = run_designer(
        DivertorSilhouetteDesigner,
        params,
        build_config["Divertor silhouette"],
        wall=wall_shape,
    )
    ivc_boundary = IVCBoundaryDesigner(params, wall_shape=wall_shape).execute()
    plasma_face = PlasmaFaceDesigner(
        params,
        ivc_boundary=ivc_boundary,
        wall_boundary=wall_shape,
        divertor_silhouette=divertor_shapes,
    ).execute()
    return ivc_boundary, plasma_face, ivc_boundary
