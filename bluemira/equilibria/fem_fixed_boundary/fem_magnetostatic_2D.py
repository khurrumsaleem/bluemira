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
Bluemira module for the solution of a 2D magnetostatic problem with cylindrical symmetry
and toroidal current source using fenics FEM solver
"""
from typing import Callable, Iterable, Optional, Union

import dolfin
import matplotlib.pyplot as plt
import numpy as np
from mpl_toolkits.axes_grid1 import make_axes_locatable

from bluemira.base.constants import MU_0
from bluemira.base.file import try_get_bluemira_path
from bluemira.base.look_and_feel import bluemira_print_flush
from bluemira.equilibria.constants import DPI_GIF, PLT_PAUSE
from bluemira.equilibria.fem_fixed_boundary.utilities import (
    ScalarSubFunc,
    find_magnetic_axis,
)
from bluemira.equilibria.plotting import PLOT_DEFAULTS
from bluemira.utilities.plot_tools import make_gif, save_figure


class FemMagnetostatic2d:
    """
    A 2D magnetostic solver. The solver is thought as support for the fem fixed
    boundary module and it is limited to axisymmetric magnetostatic problem
    with toroidal current sources. The Maxwell equations, as function of the poloidal
    magnetic flux (:math:`\\Psi`), are then reduced to the form ([Zohm]_, page 25):

    .. math::
        r^2 \\nabla\\cdot\\left(\\frac{\\nabla\\Psi}{r^2}\\right) = 2
        \\pi r \\mu_0 J_{\\Phi}

    whose weak formulation is defined as ([Villone]_):

    .. math::
        \\int_{D_p} {\\frac{1}{r}}{\\nabla}{\\Psi}{\\cdot}{\\nabla} v \\,dr\\,dz = 2
        \\pi \\mu_0 \\int_{D_p} J_{\\Phi} v \\,dr\\,dz

    where :math:`v` is the basis element function of the defined functional subspace
    :math:`V`.

    .. [Zohm] H. Zohm, Magnetohydrodynamic Stability of Tokamaks, Wiley-VCH, Germany,
       2015
    .. [Villone] VILLONE, F. et al. Plasma Phys. Control. Fusion 55 (2013) 095008,
       https://doi.org/10.1088/0741-3335/55/9/095008

    Parameters
    ----------
    p_order : int
        Order of the approximating polynomial basis functions
    """

    def __init__(self, p_order: int = 3):
        self.p_order = p_order

    def set_mesh(
        self, mesh: Union[dolfin.Mesh, str], boundaries: Union[dolfin.Mesh, str] = None
    ):
        """
        Set the mesh for the solver

        Parameters
        ----------
        mesh : Union[dolfin.Mesh, str]
            Filename of the xml file with the mesh definition or a dolfin mesh
        boundaries : Union[dolfin.Mesh, str]
            Filename of the xml file with the boundaries definition or a MeshFunction
            that defines the boundaries
        """
        # check whether mesh is a filename or a mesh, then load it or use it
        self.mesh = dolfin.Mesh(mesh) if isinstance(mesh, str) else mesh

        # define boundaries
        if boundaries is None:
            # initialize the MeshFunction
            self.boundaries = dolfin.MeshFunction(
                "size_t", mesh, mesh.topology().dim() - 1
            )
        elif isinstance(boundaries, str):
            # check wether boundaries is a filename or a MeshFunction,
            # then load it or use it
            self.boundaries = dolfin.MeshFunction(
                "size_t", self.mesh, boundaries
            )  # define the boundaries
        else:
            self.boundaries = boundaries

        # define the function space and bilinear forms
        # the Continuos Galerkin function space has been chosen as suitable for the
        # solution of the magnetostatic weak formulation in a Soblev Space H1(D)
        self.V = dolfin.FunctionSpace(self.mesh, "CG", self.p_order)

        # define trial and test functions
        self.u = dolfin.TrialFunction(self.V)
        self.v = dolfin.TestFunction(self.V)

        # Define r
        r = dolfin.Expression("x[0]", degree=self.p_order)

        self.a = (
            1
            / (2.0 * dolfin.pi * MU_0)
            * (1 / r * dolfin.dot(dolfin.grad(self.u), dolfin.grad(self.v)))
            * dolfin.dx
        )

        # initialize solution
        self.psi = dolfin.Function(self.V)
        self.psi.set_allow_extrapolation(True)
        self._psi_ax = None
        self._psi_b = None

    def define_g(self, g: Union[dolfin.Expression, dolfin.Function]):
        """
        Define g, the right hand side function of the Poisson problem

        Parameters
        ----------
        g : Union[dolfin.Expression, dolfin.Function]
            Right hand side function of the Poisson problem
        """
        self.g = g

    def solve(
        self,
        dirichlet_bc_function: Union[dolfin.Expression, dolfin.Function] = None,
        dirichlet_marker: int = None,
        neumann_bc_function: Union[dolfin.Expression, dolfin.Function] = None,
    ) -> dolfin.Function:
        """
        Solve the weak formulation maxwell equation given a right hand side g,
        Dirichlet and Neumann boundary conditions.

        Parameters
        ----------
        dirichlet_bc_function : Union[dolfin.Expression, dolfin.Function]
            Dirichlet boundary condition function
        dirichlet_marker : int
            Identification number for the dirichlet boundary
        neumann_bc_function : Union[dolfin.Expression, dolfin.Function]
            Neumann boundary condition function

        Returns
        -------
        psi : dolfin.Function
            Poloidal magnetic flux as solution of the magnetostatic problem
        """
        if neumann_bc_function is None:
            neumann_bc_function = dolfin.Expression("0.0", degree=self.p_order)

        # define the right hand side
        self.L = self.g * self.v * dolfin.dx - neumann_bc_function * self.v * dolfin.ds

        # define the Dirichlet boundary conditions
        if dirichlet_bc_function is None:
            dirichlet_bc_function = dolfin.Expression("0.0", degree=self.p_order)
            dirichlet_bc = dolfin.DirichletBC(
                self.V, dirichlet_bc_function, "on_boundary"
            )
        else:
            dirichlet_bc = dolfin.DirichletBC(
                self.V, dirichlet_bc_function, self.boundaries, dirichlet_marker
            )
        self.bcs = [dirichlet_bc]

        # solve the system taking into account the boundary conditions
        dolfin.solve(
            self.a == self.L,
            self.psi,
            self.bcs,
            solver_parameters={"linear_solver": "default"},
        )

        # Reset cached psi-axis and psi-boundary property
        self._psi_ax = None
        self._psi_b = None
        return self.psi

    def calculate_b(self) -> dolfin.Function:
        """
        Calculates the magnetic field intensity from psi

        Note: code from Fenics_tutorial (
        https://link.springer.com/book/10.1007/978-3-319-52462-7), pag. 104
        """
        # new function space for mapping B as vector
        w = dolfin.VectorFunctionSpace(self.mesh, "CG", 1)

        r = dolfin.Expression("x[0]", degree=1)

        # calculate derivatives
        Bx = -self.psi.dx(1) / (2 * dolfin.pi * r)
        Bz = self.psi.dx(0) / (2 * dolfin.pi * r)

        # project B as vector to new function space
        self.B = dolfin.project(dolfin.as_vector((Bx, Bz)), w)

        return self.B


class FemGradShafranovFixedBoundary(FemMagnetostatic2d):
    """
    A 2D fem Grad Shafranov solver. The solver is thought as support for the fem fixed
    boundary module.

    Parameters
    ----------
    p_order : int
        Order of the approximating polynomial basis functions
    max_iter: int
        Maximum number of iterations
    iter_err_max: float
        Convergence criterion value
    relaxation: float
        Relaxation factor for the Picard iteration procedure
    """

    def __init__(
        self,
        p_order: int = 3,
        max_iter: int = 10,
        iter_err_max: float = 1e-5,
        relaxation: float = 0.0,
    ):
        super().__init__(p_order)
        self.iter_err_max = iter_err_max
        self.max_iter = max_iter
        self.relaxation = relaxation
        self.k = 1

    @property
    def psi_ax(self) -> float:
        """Poloidal flux on the magnetic axis"""
        if self._psi_ax is None:
            self._psi_ax = self.psi(find_magnetic_axis(self.psi, self.mesh))
        return self._psi_ax

    @property
    def psi_b(self) -> float:
        """Poloidal flux on the boundary"""
        if self._psi_b is None:
            self._psi_b = np.min(self.psi.vector()[:])
        return self._psi_b

    @property
    def psi_norm_2d(self) -> Callable[[np.ndarray], float]:
        """Normalized flux function in 2-D"""
        return lambda x: np.sqrt(
            np.abs((self.psi(x) - self.psi_ax) / (self.psi_b - self.psi_ax))
        )

    def _create_g_func(
        self,
        pprime: Union[Callable[[np.ndarray], np.ndarray], float],
        ffprime: Union[Callable[[np.ndarray], np.ndarray], float],
        curr_target: Optional[float],
    ) -> Callable[[np.ndarray], float]:
        """
        Return the density current function given pprime and ffprime.

        Parameters
        ----------
        pprime: Union[callable, float]
            pprime as function of psi_norm (1-D function)
        ffprime: Union[callable, float]
            ffprime as function of psi_norm (1-D function)
        curr_target: float
            Target current (also used to initialize the solution in case self.psi is
            still 0 and pprime and ffprime are, then, not defined) [A]

        Returns
        -------
        g: callable
            Source current to solve the magnetostatic problem
        """
        area = dolfin.assemble(
            dolfin.Constant(1) * dolfin.Measure("dx", domain=self.mesh)()
        )

        j_target = curr_target / area if curr_target else 1.0

        def g(x):
            if self.psi_ax == 0:
                return j_target
            else:
                r = x[0]
                x_psi = self.psi_norm_2d(x)

                a = r * (pprime(x_psi) if callable(pprime) else pprime)
                b = 1 / MU_0 / r * (ffprime(x_psi) if callable(ffprime) else ffprime)

                return self.k * (a + b)

        return g

    def define_g(
        self,
        pprime: Union[Callable[[np.ndarray], np.ndarray], float],
        ffprime: Union[Callable[[np.ndarray], np.ndarray], float],
        curr_target: Optional[float],
    ):
        """
        Return the density current DOLFIN function given pprime and ffprime.

        Parameters
        ----------
        pprime: Union[Callable[[np.ndarray], np.ndarray]
            pprime as function of psi_norm (1-D function)
        ffprime: Union[Callable[[np.ndarray], np.ndarray]
            ffprime as function of psi_norm (1-D function)
        curr_target: float
            Target current (also used to initialize the solution in case self.psi is
            still 0 and pprime and ffprime are, then, not defined).
            If None, plasma current is calculated and not constrained
        """
        self._curr_target = curr_target
        self._g_func = self._create_g_func(pprime, ffprime, self._curr_target)
        super().define_g(ScalarSubFunc(self._g_func))

    def _calculate_curr_tot(self) -> float:
        """Calculate the total current into the domain"""
        return dolfin.assemble(self.g * dolfin.Measure("dx", domain=self.mesh)())

    def _update_curr(self):
        self.k = 1
        if self._curr_target:
            self.k = self._curr_target / self._calculate_curr_tot()

    def solve(
        self,
        dirichlet_bc_function: Optional[
            Union[dolfin.Expression, dolfin.Function]
        ] = None,
        dirichlet_marker: Optional[int] = None,
        neumann_bc_function: Optional[Union[dolfin.Expression, dolfin.Function]] = None,
        plot: bool = False,
        debug: bool = False,
        gif: bool = False,
    ) -> dolfin.Function:
        """
        Solve the G-S problem.

        Parameters
        ----------
        dirichlet_bc_function : Optional[Union[dolfin.Expression, dolfin.Function]]
            Dirichlet boundary condition function. Defaults to a Dirichlet boundary
            condition of 0 on the plasma boundary.
        dirichlet_marker : int
            Identification number for the dirichlet boundary
        neumann_bc_function : Optional[Union[dolfin.Expression, dolfin.Function]]
            Neumann boundary condition function. Defaults to a Neumann boundary
            condition of 0 on the plasma boundary.
        plot: bool
            Whether or not to plot

        Returns
        -------
        psi: dolfin.Function
            dolfin.Function for psi
        """
        points = self.mesh.coordinates()
        plot = any((plot, debug, gif))
        folder = try_get_bluemira_path(
            "", subfolder="generated_data", allow_missing=False
        )
        figname = "Fixed boundary equilibrium iteration "

        super().solve(dirichlet_bc_function, dirichlet_marker, neumann_bc_function)

        if plot:
            f, ax, cax = self._setup_plot(debug)

        self._update_curr()

        diff = np.zeros(len(points))
        for i in range(1, self.max_iter + 1):
            prev_psi = self.psi.vector()[:]
            prev = np.array([self.psi_norm_2d(p) for p in points])

            if plot:
                self._plot_current_iteration(f, ax, cax, i, points, prev, diff, debug)
                if debug or gif:
                    save_figure(
                        f,
                        figname + str(i),
                        save=True,
                        folder=folder,
                        dpi=DPI_GIF,
                    )

            super().solve(dirichlet_bc_function, dirichlet_marker, neumann_bc_function)

            new = np.array([self.psi_norm_2d(p) for p in points])
            diff = new - prev

            eps = np.linalg.norm(diff, ord=2) / np.linalg.norm(new, ord=2)

            bluemira_print_flush(
                f"iter = {i} eps = {eps:.3E} psi_ax : {self.psi_ax:.2f}"
            )

            # Update psi in-place (Fenics handles this with the below syntax)
            self.psi.vector()[:] = (1 - self.relaxation) * self.psi.vector()[
                :
            ] + self.relaxation * prev_psi

            self._update_curr()

            if eps < self.iter_err_max:
                break

        if plot:
            plt.close(f)
        if gif:
            make_gif(folder, figname, clean=not debug)

        return self.psi

    def _setup_plot(self, debug):
        n_col = 3 if debug else 2
        fig, ax = plt.subplots(1, n_col, figsize=(18, 10))
        plt.subplots_adjust(wspace=0.5)

        cax = []
        for axis in ax:
            divider = make_axes_locatable(axis)
            cax.append(divider.append_axes("right", size="10%", pad=0.1))

        return fig, ax, cax

    def _plot_current_iteration(
        self,
        f,
        ax,
        cax,
        i_iter: int,
        points: Iterable,
        prev: np.ndarray,
        diff: np.ndarray,
        debug: bool,
    ):
        for axis in ax:
            axis.clear()
            axis.set_xlabel("x")
            axis.set_ylabel("z")
            axis.set_aspect("equal")

        cm = self._plot_array(
            ax[0],
            points,
            np.array([self._g_func(p) for p in points]),
            f"({i_iter}) " + "$J_{tor}$",
            PLOT_DEFAULTS["current"]["cmap"],
        )
        self._add_colorbar(cm, cax[0], "A/m$^{2}$\n")

        levels = np.linspace(0, 1, 11)
        cm = self._plot_array(
            ax[1],
            points,
            prev,
            f"({i_iter}) " + "$\\Psi_{n}$",
            PLOT_DEFAULTS["psi"]["cmap"],
            levels,
        )
        self._add_colorbar(cm, cax[1], "")

        if debug:
            cm = self._plot_array(
                ax[2],
                points,
                100 * diff,
                f"({i_iter}) " + "$\\Psi_{n}$ error",
                "seismic",
            )
            self._add_colorbar(cm, cax[2], "%")

        plt.pause(PLT_PAUSE)

    def _plot_array(
        self,
        ax,
        points: np.ndarray,
        array: np.ndarray,
        title: str,
        cmap: str,
        levels: Optional[np.ndarray] = None,
    ):
        cm = ax.tricontourf(points[:, 0], points[:, 1], array, cmap=cmap, levels=levels)
        ax.tricontour(
            points[:, 0], points[:, 1], array, colors="k", linewidths=0.5, levels=levels
        )

        ax.set_title(title)
        return cm

    @staticmethod
    def _add_colorbar(cm, cax, title):
        last_axes = plt.gca()
        ax = cm.axes
        fig = ax.figure
        cb = fig.colorbar(cm, cax=cax)
        cax.set_title(title)
        plt.sca(last_axes)
