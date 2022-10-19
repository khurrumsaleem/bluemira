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

import dolfinx
import matplotlib.pyplot as plt
import numpy as np

from bluemira.base.components import PhysicalComponent
from bluemira.base.constants import MU_0
from bluemira.equilibria.fem_fixed_boundary.fem_magnetostatic_2D import (
    FemMagnetostatic2d,
)
from bluemira.equilibria.fem_fixed_boundary.utilities import Solovev, plot_scalar_field
from bluemira.geometry.face import BluemiraFace
from bluemira.geometry.tools import interpolate_bspline
from bluemira.geometry.wire import BluemiraWire
from bluemira.mesh import meshing
from bluemira.mesh.tools import import_mesh, msh_to_xdmf


class TestSolovev:
    def test_Solovev_Zheng(self):  # noqa: N803
        """
        Compare the psi Solovev analytical solution as described in [Zheng1996] with the
        one calculated using the implemented magnetostic module.

        .. [Zheng1996] S. B. Zheng, A. J. Wootton, and Emilia R. Solano , "Analytical
           tokamak equilibrium for shaped plasmas", Physics of Plasmas 3, 1176-1178 (
           1996) https://doi.org/10.1063/1.871772
        """

        # set problem parameters
        R0 = 9.07  # noqa: N806
        A = 3.1
        delta = 0.5
        kappa = 1.7
        a = R0 / A

        # Solovev parameters for pprime and ffprime
        A1 = -6.84256806e-02  # noqa: N806
        A2 = -6.52918977e-02  # noqa: N806

        # create the Solovev instance to get the exact psi
        solovev = Solovev(R0, a, kappa, delta, A1, A2)

        levels = 50
        axis, cntr, _, _, psi_exact = solovev.plot_psi(
            5.0, -6, 8.0, 12.0, 100, 100, levels=levels
        )
        plt.show()

        # get the plasma boundary finding the contour at psi = 0
        levels = [0]
        axis, cntr, _, _, psi_exact = solovev.plot_psi(
            6.0, -5, 6.0, 10.0, 500, 500, levels=levels, tofill=False
        )

        plt.show()

        ind0 = np.where(np.array(levels) == 0.0)[0][0]
        boundary = cntr.collections[ind0].get_paths()[0].vertices
        boundary = np.hstack(
            (boundary, np.zeros((boundary.shape[0], 1), dtype=boundary.dtype))
        )

        # create the PhysicalComponent for the plasma
        curve1 = interpolate_bspline(
            boundary[0 : int(len(boundary) / 2)], label="curve1"
        )
        curve2 = interpolate_bspline(
            boundary[int(len(boundary) / 2 - 1) : len(boundary)], label="curve2"
        )
        lcfs = BluemiraWire([curve1, curve2], "LCFS")
        lcfs.mesh_options = {"lcar": 0.05, "physical_group": "lcfs"}

        plasma_face = BluemiraFace(lcfs, "plasma_face")
        plasma_face.mesh_options = {"lcar": 0.2, "physical_group": "plasma_face"}

        plasma = PhysicalComponent("Plasma", shape=plasma_face)

        plasma.plot_options.view = "xy"
        plasma.plot_2d()
        plt.show()

        # mesh the plasma
        meshing.Mesh()(plasma)

        msh_to_xdmf("Mesh.msh", dimensions=2, directory=".")

        mesh, boundaries, _, _ = import_mesh(
            "Mesh",
            directory=".",
            subdomains=True,
        )

        dolfinx.plot(mesh)
        plt.show()

        # initialize the Grad-Shafranov solver
        p = 2
        gs_solver = FemMagnetostatic2d(p_order=p)
        gs_solver.set_mesh(mesh, boundaries)

        # Set the right hand side of the Grad-Shafranov equation, as a function of psi
        g = dolfinx.fem.Expression(
            "1/mu0*(-x[0]*A1 + A2/x[0])",
            A1=solovev.A1,
            A2=solovev.A2,
            mu0=MU_0,
            degree=p,
        )
        gs_solver.define_g(g)

        # solve the Grad-Shafranov equation
        psi_calc = gs_solver.solve()

        # calculate the GS and analytic solution on the mesh points
        mesh_points = mesh.coordinates()
        psi_calc_data = np.array([psi_calc(x) for x in mesh_points])
        psi_exact = solovev.psi(mesh_points)

        levels = np.linspace(min(psi_exact), max(psi_exact), 25)
        axis, cntr, _ = plot_scalar_field(
            mesh_points[:, 0],
            mesh_points[:, 1],
            psi_exact,
            levels=levels,
            axis=None,
            tofill=False,
        )

        plt.show()

        axis = None
        axis, cntr, _ = plot_scalar_field(
            mesh_points[:, 0],
            mesh_points[:, 1],
            psi_exact,
            levels=20,
            axis=axis,
            tofill=True,
        )
        plt.show()

        error = abs(psi_calc_data - psi_exact)

        levels = np.linspace(0.0, max(error) * 1.1, 50)
        axis, cntr, _ = plot_scalar_field(
            mesh_points[:, 0],
            mesh_points[:, 1],
            error,
            levels=levels,
            axis=None,
            tofill=True,
        )
        plt.show()

        # calculate the error norm
        diff = psi_calc_data - psi_exact
        eps = np.linalg.norm(diff, ord=2) / np.linalg.norm(psi_exact, ord=2)

        assert eps < 1e-4
