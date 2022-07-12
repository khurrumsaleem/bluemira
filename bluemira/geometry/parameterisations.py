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
Geometry parameterisations
"""

from __future__ import annotations

import abc
import json
from enum import Enum
from functools import partial
from typing import Dict, Iterable, Optional, TextIO, Union

import numpy as np
from scipy.special import iv as bessel

from bluemira.geometry._deprecated_tools import distance_between_points
from bluemira.geometry.error import GeometryParameterisationError
from bluemira.geometry.tools import (
    interpolate_bspline,
    make_bezier,
    make_circle,
    make_circle_arc_3P,
    make_polygon,
    wire_closure,
)
from bluemira.geometry.wire import BluemiraWire
from bluemira.utilities.opt_variables import BoundedVariable, OptVariables

__all__ = [
    "GeometryParameterisation",
    "PictureFrame",
    "PolySpline",
    "PrincetonD",
    "SextupleArc",
    "TripleArc",
]


class GeometryParameterisation(abc.ABC):
    """
    A geometry parameterisation class facilitating geometry optimisation.

    Notes
    -----
    Subclass this base class when making a new GeometryParameterisation, adding a set of
    variables with initial values, and override the create_shape method.
    """

    __slots__ = ("name", "variables", "n_ineq_constraints")

    def __init__(self, variables: OptVariables):
        """
        Parameters
        ----------
        variables: OptVariables
            Set of optimisation variables of the GeometryParameterisation
        """
        self.name = self.__class__.__name__
        self.variables = variables
        self.n_ineq_constraints = 0
        super().__init__()

    def adjust_variable(self, name, value=None, lower_bound=None, upper_bound=None):
        """
        Adjust a variable in the GeometryParameterisation.

        Parameters
        ----------
        name: str
            Name of the variable to adjust
        value: Optional[float]
            Value of the variable to set
        lower_bound: Optional[float]
            Value of the lower bound to set
        upper_bound: Optional[float]
            Value of the upper to set
        """
        self.variables.adjust_variable(name, value, lower_bound, upper_bound)

    def fix_variable(self, name, value=None):
        """
        Fix a variable in the GeometryParameterisation, removing it from optimisation
        but preserving a constant value.

        Parameters
        ----------
        name: str
            Name of the variable to fix
        value: Optional[float]
            Value at which to fix the variable (will default to present value)
        """
        self.variables.fix_variable(name, value)

    def shape_ineq_constraints(self, constraint, x, grad):
        """
        Inequality constraint function for the variable vector of the geometry
        parameterisation. This is used when internal consistency between different
        un-fixed variables is required.

        Parameters
        ----------
        constraint: np.ndarray
            Constraint vector (assign in place)
        x: np.ndarray
            Normalised vector of free variables
        grad: np.ndarray
            Gradient matrix of the constraint (assign in place)
        """
        if self.n_ineq_constraints < 1:
            raise GeometryParameterisationError(
                f"Cannot apply shape_ineq_constraints to {self.__class__.__name__}: it"
                "has no inequality constraints."
            )

    def _process_x_norm_fixed(self, x_norm):
        """
        Utility for processing a set of free, normalised variables, and folding the fixed
        un-normalised variables back into a single list of all actual values.

        Parameters
        ----------
        x_norm: np.ndarray
            Normalised vector of variable values

        Returns
        -------
        x_actual: list
            List of ordered actual (un-normalised) values
        """
        fixed_idx = self.variables._fixed_variable_indices

        # Note that we are dealing with normalised values when coming from the optimiser
        x_actual = list(self.variables.get_values_from_norm(x_norm))

        if fixed_idx:
            x_fixed = self.variables.values
            for i in fixed_idx:
                x_actual.insert(i, x_fixed[i])
        return x_actual

    def _get_x_norm_index(self, name: str):
        """
        Get the index of a variable name in the modified-length x_norm vector

        Parameters
        ----------
        name: str
            Variable name for which to get the index

        Returns
        -------
        idx_x_norm: int
            Index of the variable name in the modified-length x_norm vector
        """
        fixed_idx = self.variables._fixed_variable_indices
        idx_actual = self.variables.names.index(name)

        if not fixed_idx:
            return idx_actual

        count = 0
        for idx_fx in fixed_idx:
            if idx_actual > idx_fx:
                count += 1
        return idx_actual - count

    @abc.abstractmethod
    def create_shape(self, label="", **kwargs) -> BluemiraWire:
        """
        Make a CAD representation of the geometry.

        Parameters
        ----------
        label: str, default = ""
            Label to give the wire

        Returns
        -------
        shape: BluemiraWire
            CAD Wire of the geometry
        """
        pass

    def to_json(self, file: str):
        """
        Write the json representation of the GeometryParameterisation to a file.

        Parameters
        ----------
        file: str
            The path to the file.
        """
        self.variables.to_json(file)

    @classmethod
    def from_json(cls, file: Union[str, TextIO]) -> GeometryParameterisation:
        """
        Create the GeometryParameterisation from a json file.

        Parameters
        ----------
        file: Union[str, TextIO]
            The path to the file, or an open file handle that supports reading.
        """
        if isinstance(file, str):
            with open(file, "r") as fh:
                return cls.from_json(fh)

        var_dict = json.load(file)
        return cls(var_dict)


class PrincetonD(GeometryParameterisation):
    """
    Princeton D geometry parameterisation.

    Parameters
    ----------
    var_dict: Optional[dict]
        Dictionary with which to update the default values of the parameterisation.
    """

    __slots__ = ()

    def __init__(self, var_dict=None):
        variables = OptVariables(
            [
                BoundedVariable(
                    "x1", 4, lower_bound=2, upper_bound=6, descr="Inboard limb radius"
                ),
                BoundedVariable(
                    "x2",
                    14,
                    lower_bound=10,
                    upper_bound=18,
                    descr="Outboard limb radius",
                ),
                BoundedVariable(
                    "dz",
                    0,
                    lower_bound=-0.5,
                    upper_bound=0.5,
                    descr="Vertical offset from z=0",
                ),
            ],
            frozen=True,
        )
        variables.adjust_variables(var_dict, strict_bounds=False)

        super().__init__(variables)
        self.n_ineq_constraints = 1

    def create_shape(self, label="", n_points=2000):
        """
        Make a CAD representation of the Princeton D.

        Parameters
        ----------
        label: str, default = ""
            Label to give the wire
        n_points: int
            The number of points to use when calculating the geometry of the Princeton
            D.

        Returns
        -------
        shape: BluemiraWire
            CAD Wire of the geometry
        """
        x, z = self._princeton_d(
            *self.variables.values,
            n_points,
        )
        xyz = np.array([x, np.zeros(len(x)), z])

        outer_arc = interpolate_bspline(
            xyz.T,
            label="outer_arc",
            # start_tangent=[0, 0, 1],
            # end_tangent=[0, 0, -1],
        )
        # TODO: Enforce tangency of this bspline... causing issues with offsetting
        # TODO: The real irony is that tangencies don't solve the problem..
        straight_segment = wire_closure(outer_arc, label="straight_segment")
        return BluemiraWire([outer_arc, straight_segment], label=label)

    def shape_ineq_constraints(self, constraint, x_norm, grad):
        """
        Inequality constraint function for the variable vector of the geometry
        parameterisation.

        Parameters
        ----------
        constraint: np.ndarray
            Constraint vector (assign in place)
        x: np.ndarray
            Normalised vector of free variables
        grad: np.ndarray
            Gradient matrix of the constraint (assign in place)
        """
        x_actual = self._process_x_norm_fixed(x_norm)

        x1, x2, _ = x_actual

        constraint[0] = x1 - x2

        idx_x1 = self._get_x_norm_index("x1")
        idx_x2 = self._get_x_norm_index("x2")

        if grad.size > 0:
            grad[:] = np.zeros(len(x_norm))
            if not self.variables["x1"].fixed:
                grad[0, idx_x1] = 1
            if not self.variables["x2"].fixed:
                grad[0, idx_x2] = -1

        return constraint

    @staticmethod
    def _princeton_d(x1, x2, dz, npoints=2000):
        """
        Princeton D shape calculation (e.g. Gralnick and Tenney, 1976, or
        File, Mills, and Sheffield, 1971)

        Parameters
        ----------
        x1: float
            The inboard centreline radius of the Princeton D
        x2: float
            The outboard centreline radius of the Princeton D
        dz: float
            The vertical offset (from z=0)
        npoints: int (default = 2000)
            The size of the x, z coordinate sets to return

        Returns
        -------
        x: np.array(npoints)
            The x coordinates of the Princeton D shape
        z: np.array(npoints)
            The z coordinates of the Princeton D shape

        Note
        ----
        Returns an open set of coordinates

        :math:`x = X_{0}e^{ksin(\\theta)}`
        :math:`z = X_{0}k\\Bigg[\\theta I_{1}(k)+\\sum_{n=1}^{\\infty}{\\frac{i}{n}
        e^{\\frac{in\\pi}{2}}\\bigg(e^{-in\\theta}-1\\bigg)\\bigg(1+e^{in(\\theta+\\pi)}
        \\bigg)\\frac{I_{n-1}(k)+I_{n+1}(k)}{2}}\\Bigg]`

        Where:
            :math:`X_{0} = \\sqrt{x_{1}x_{2}}`
            :math:`k = \\frac{ln(x_{2}/x_{1})}{2}`

        Where:
            :math:`I_{n}` is the n-th order modified Bessel function
            :math:`x_{1}` is the inner radial position of the shape
            :math:`x_{2}` is the outer radial position of the shape
        """  # noqa :W505
        if x2 <= x1:
            raise GeometryParameterisationError(
                "Princeton D parameterisation requires an x2 value "
                f"greater than x1: {x1} >= {x2}"
            )

        xo = np.sqrt(x1 * x2)
        k = 0.5 * np.log(x2 / x1)
        theta = np.linspace(-0.5 * np.pi, 1.5 * np.pi, npoints)
        s = np.zeros(npoints, dtype="complex128")
        n = 0
        while True:  # sum convergent series
            n += 1

            ds = 1j / n * (np.exp(-1j * n * theta) - 1)
            ds *= 1 + np.exp(1j * n * (theta + np.pi))
            ds *= np.exp(1j * n * np.pi / 2)
            ds *= (bessel(n - 1, k) + bessel(n + 1, k)) / 2
            s += ds
            if np.max(abs(ds)) < 1e-14:
                break

        z = abs(xo * k * (bessel(1, k) * theta + s))
        x = xo * np.exp(k * np.sin(theta))
        z -= np.mean(z)
        z += dz  # vertical shift
        return x, z


class TripleArc(GeometryParameterisation):
    """
    Triple-arc up-down symmetric geometry parameterisation.

    Parameters
    ----------
    var_dict: Optional[dict]
        Dictionary with which to update the default values of the parameterisation.
    """

    __slots__ = ()

    def __init__(self, var_dict=None):
        variables = OptVariables(
            [
                BoundedVariable(
                    "x1", 4.486, lower_bound=4, upper_bound=5, descr="Inner limb radius"
                ),
                BoundedVariable(
                    "dz",
                    0,
                    lower_bound=-1,
                    upper_bound=1,
                    descr="Vertical offset from z=0",
                ),
                BoundedVariable(
                    "sl", 6.428, lower_bound=5, upper_bound=10, descr="Straight length"
                ),
                BoundedVariable(
                    "f1", 3, lower_bound=2, upper_bound=12, descr="rs == f1*z small"
                ),
                BoundedVariable(
                    "f2", 4, lower_bound=2, upper_bound=12, descr="rm == f2*rs mid"
                ),
                BoundedVariable(
                    "a1",
                    20,
                    lower_bound=5,
                    upper_bound=120,
                    descr="Small arc angle [degrees]",
                ),
                BoundedVariable(
                    "a2",
                    40,
                    lower_bound=10,
                    upper_bound=120,
                    descr="Middle arc angle [degrees]",
                ),
            ],
            frozen=True,
        )
        variables.adjust_variables(var_dict, strict_bounds=False)
        super().__init__(variables)
        self.n_ineq_constraints = 1

    def shape_ineq_constraints(self, constraint, x_norm, grad):
        """
        Inequality constraint function for the variable vector of the geometry
        parameterisation.

        Parameters
        ----------
        constraint: np.ndarray
            Contraint vector (assign in place)
        x: np.ndarray
            Normalised vector of free variables
        grad: np.ndarray
            Gradient matrix of the constraint (assign in place)
        """
        x_actual = self._process_x_norm_fixed(x_norm)

        _, _, _, _, _, a1, a2 = x_actual

        constraint[0] = a1 + a2 - 180

        idx_a1 = self._get_x_norm_index("a1")
        idx_a2 = self._get_x_norm_index("a2")

        if grad.size > 0:
            g = np.zeros(len(x_norm))
            if not self.variables["a1"].fixed:
                g[idx_a1] = 1
            if not self.variables["a2"].fixed:
                g[idx_a2] = 1
            grad[0, :] = g

        return constraint

    def create_shape(self, label=""):
        """
        Make a CAD representation of the triple arc.

        Parameters
        ----------
        label: str, default = ""
            Label to give the wire

        Returns
        -------
        shape: BluemiraWire
            CAD Wire of the geometry
        """
        x1, dz, sl, f1, f2, a1, a2 = self.variables.values
        a1, a2 = np.deg2rad(a1), np.deg2rad(a2)

        z1 = 0.5 * sl
        # Upper half
        p1 = [x1, 0, z1]
        atot = a1 + a2
        a15 = 0.5 * a1
        p15 = [x1 + f1 * (1 - np.cos(a15)), 0, z1 + f1 * np.sin(a15)]
        p2 = [x1 + f1 * (1 - np.cos(a1)), 0, z1 + f1 * np.sin(a1)]

        a25 = a1 + 0.5 * a2
        p25 = [
            p2[0] + f2 * (np.cos(a1) - np.cos(a25)),
            0,
            p2[2] + f2 * (np.sin(a25) - np.sin(a1)),
        ]
        p3 = [
            p2[0] + f2 * (np.cos(a1) - np.cos(atot)),
            0,
            p2[2] + f2 * (np.sin(atot) - np.sin(a1)),
        ]
        rl = p3[2] / np.sin(np.pi - atot)

        a35 = 0.5 * atot
        p35 = [
            p3[0] + rl * (np.cos(a35) - np.cos(np.pi - atot)),
            0,
            p3[2] - rl * (np.sin(atot) - np.sin(a35)),
        ]
        p4 = [
            p3[0] + rl * (1 - np.cos(np.pi - atot)),
            0,
            p3[2] - rl * np.sin(atot),
        ]

        # Symmetric lower half
        p45 = [p35[0], 0, -p35[2]]
        p5 = [p3[0], 0, -p3[2]]
        p55 = [p25[0], 0, -p25[2]]
        p6 = [p2[0], 0, -p2[2]]
        p65 = [p15[0], 0, -p15[2]]
        p7 = [p1[0], 0, -p1[2]]

        wires = [
            make_circle_arc_3P(p1, p15, p2, label="upper_inner_arc"),
            make_circle_arc_3P(p2, p25, p3, label="upper_mid_arc"),
            make_circle_arc_3P(p3, p35, p4, label="upper_outer_arc"),
            make_circle_arc_3P(p4, p45, p5, label="lower_outer_arc"),
            make_circle_arc_3P(p5, p55, p6, label="lower_mid_arc"),
            make_circle_arc_3P(p6, p65, p7, label="lower_inner_arc"),
        ]

        if sl != 0.0:
            straight_segment = wire_closure(
                BluemiraWire(wires), label="straight_segment"
            )
            wires.append(straight_segment)

        wire = BluemiraWire(wires, label=label)
        wire.translate((0, 0, dz))
        return wire


class SextupleArc(GeometryParameterisation):
    """
    Sextuple-arc up-down asymmetric geometry parameterisation.

    Parameters
    ----------
    var_dict: Optional[dict]
        Dictionary with which to update the default values of the parameterisation.
    """

    __slots__ = ()

    def __init__(self, var_dict=None):
        variables = OptVariables(
            [
                BoundedVariable(
                    "x1", 4.486, lower_bound=4, upper_bound=5, descr="Inner limb radius"
                ),
                BoundedVariable(
                    "z1", 5, lower_bound=0, upper_bound=10, descr="Inboard limb height"
                ),
                BoundedVariable(
                    "r1", 4, lower_bound=4, upper_bound=12, descr="1st arc radius"
                ),
                BoundedVariable(
                    "r2", 5, lower_bound=4, upper_bound=12, descr="2nd arc radius"
                ),
                BoundedVariable(
                    "r3", 6, lower_bound=4, upper_bound=12, descr="3rd arc radius"
                ),
                BoundedVariable(
                    "r4", 7, lower_bound=4, upper_bound=12, descr="4th arc radius"
                ),
                BoundedVariable(
                    "r5", 8, lower_bound=4, upper_bound=12, descr="5th arc radius"
                ),
                BoundedVariable(
                    "a1",
                    45,
                    lower_bound=5,
                    upper_bound=50,
                    descr="1st arc angle [degrees]",
                ),
                BoundedVariable(
                    "a2",
                    60,
                    lower_bound=10,
                    upper_bound=80,
                    descr="2nd arc angle [degrees]",
                ),
                BoundedVariable(
                    "a3",
                    90,
                    lower_bound=10,
                    upper_bound=100,
                    descr="3rd arc angle [degrees]",
                ),
                BoundedVariable(
                    "a4",
                    40,
                    lower_bound=10,
                    upper_bound=80,
                    descr="4th arc angle [degrees]",
                ),
                BoundedVariable(
                    "a5",
                    30,
                    lower_bound=10,
                    upper_bound=80,
                    descr="5th arc angle [degrees]",
                ),
            ],
            frozen=True,
        )
        variables.adjust_variables(var_dict, strict_bounds=False)
        super().__init__(variables)
        self.n_ineq_constraints = 1

    def shape_ineq_constraints(self, constraint, x_norm, grad):
        """
        Inequality constraint function for the variable vector of the geometry
        parameterisation.

        Parameters
        ----------
        constraint: np.ndarray
            Contraint vector (assign in place)
        x: np.ndarray
            Normalised vector of free variables
        grad: np.ndarray
            Gradient matrix of the constraint (assign in place)
        """
        x_actual = self._process_x_norm_fixed(x_norm)

        _, _, _, _, _, _, _, a1, a2, a3, a4, a5 = x_actual

        constraint[0] = a1 + a2 + a3 + a4 + a5 - 360
        var_strings = ["a1", "a2", "a3", "a4", "a5"]

        if grad.size > 0:
            g = np.zeros(len(x_norm))
            for var in var_strings:
                if not self.variables[var].fixed:
                    g[self._get_x_norm_index(var)] = 1

            grad[0, :] = g

        return constraint

    @staticmethod
    def _project_centroid(xc, zc, xi, zi, ri):
        vec = np.array([xi - xc, zi - zc])
        vec /= np.linalg.norm(vec)
        xc = xi - vec[0] * ri
        zc = zi - vec[1] * ri
        return xc, zc, vec

    def create_shape(self, label=""):
        """
        Make a CAD representation of the sextuple arc.

        Parameters
        ----------
        label: str, default = ""
            Label to give the wire

        Returns
        -------
        shape: BluemiraWire
            CAD Wire of the geometry
        """
        variables = self.variables.values
        x1, z1 = variables[:2]
        r_values = variables[2:7]
        a_values = np.deg2rad(variables[7:])

        wires = []
        a_start = 0
        xi, zi = x1, z1
        xc = x1 + r_values[0]
        zc = z1
        for i, (ai, ri) in enumerate(zip(a_values, r_values)):
            if i > 0:
                xc, zc, _ = self._project_centroid(xc, zc, xi, zi, ri)

            a = np.pi - a_start - ai
            xi = xc + ri * np.cos(a)
            zi = zc + ri * np.sin(a)

            start_angle = np.rad2deg(np.pi - a_start)
            end_angle = np.rad2deg(a)

            arc = make_circle(
                ri,
                center=[xc, 0, zc],
                start_angle=end_angle,
                end_angle=start_angle,
                axis=[0, -1, 0],
                label=f"arc_{i+1}",
            )

            wires.append(arc)

            a_start += ai

        xc, zc, vec = self._project_centroid(xc, zc, xi, zi, ri)

        # Retrieve last arc (could be bad...)
        r6 = (xi - x1) / (1 + vec[0])
        xc6 = xi - r6 * vec[0]
        z7 = zc6 = zi - r6 * vec[1]

        closing_arc = make_circle(
            r6,
            center=[xc6, 0, zc6],
            start_angle=180,
            end_angle=np.rad2deg(np.pi - a_start),
            axis=[0, -1, 0],
            label="arc_6",
        )

        wires.append(closing_arc)

        if not np.isclose(z1, z7):
            straight_segment = wire_closure(
                BluemiraWire(wires), label="straight_segment"
            )
            wires.append(straight_segment)

        return BluemiraWire(wires, label=label)


class PolySpline(GeometryParameterisation):
    """
    Simon McIntosh's Poly-Bézier-spline geometry parameterisation (19 variables).

    Parameters
    ----------
    var_dict: Optional[dict]
        Dictionary with which to update the default values of the parameterisation.
    """

    __slots__ = ()

    def __init__(self, var_dict=None):
        variables = OptVariables(
            [
                BoundedVariable(
                    "x1", 4.3, lower_bound=4, upper_bound=5, descr="Inner limb radius"
                ),
                BoundedVariable(
                    "x2", 16.56, lower_bound=5, upper_bound=25, descr="Outer limb radius"
                ),
                BoundedVariable(
                    "z2",
                    0.03,
                    lower_bound=-2,
                    upper_bound=2,
                    descr="Outer note vertical shift",
                ),
                BoundedVariable(
                    "height", 15.5, lower_bound=10, upper_bound=50, descr="Full height"
                ),
                BoundedVariable(
                    "top", 0.52, lower_bound=0.2, upper_bound=1, descr="Horizontal shift"
                ),
                BoundedVariable(
                    "upper", 0.67, lower_bound=0.2, upper_bound=1, descr="Vertical shift"
                ),
                BoundedVariable(
                    "dz", -0.6, lower_bound=-5, upper_bound=5, descr="Vertical offset"
                ),
                BoundedVariable(
                    "flat",
                    0,
                    lower_bound=0,
                    upper_bound=1,
                    descr="Fraction of straight outboard leg",
                ),
                BoundedVariable(
                    "tilt",
                    4,
                    lower_bound=-45,
                    upper_bound=45,
                    descr="Outboard angle [degrees]",
                ),
                BoundedVariable(
                    "bottom",
                    0.4,
                    lower_bound=0,
                    upper_bound=1,
                    descr="Lower horizontal shift",
                ),
                BoundedVariable(
                    "lower",
                    0.67,
                    lower_bound=0.2,
                    upper_bound=1,
                    descr="Lower vertical shift",
                ),
                BoundedVariable(
                    "l0s",
                    0.8,
                    lower_bound=0.1,
                    upper_bound=1.9,
                    descr="Tension variable first segment start",
                ),
                BoundedVariable(
                    "l1s",
                    0.8,
                    lower_bound=0.1,
                    upper_bound=1.9,
                    descr="Tension variable second segment start",
                ),
                BoundedVariable(
                    "l2s",
                    0.8,
                    lower_bound=0.1,
                    upper_bound=1.9,
                    descr="Tension variable third segment start",
                ),
                BoundedVariable(
                    "l3s",
                    0.8,
                    lower_bound=0.1,
                    upper_bound=1.9,
                    descr="Tension variable fourth segment start",
                ),
                BoundedVariable(
                    "l0e",
                    0.8,
                    lower_bound=0.1,
                    upper_bound=1.9,
                    descr="Tension variable first segment end",
                ),
                BoundedVariable(
                    "l1e",
                    0.8,
                    lower_bound=0.1,
                    upper_bound=1.9,
                    descr="Tension variable second segment end",
                ),
                BoundedVariable(
                    "l2e",
                    0.8,
                    lower_bound=0.1,
                    upper_bound=1.9,
                    descr="Tension variable third segment end",
                ),
                BoundedVariable(
                    "l3e",
                    0.8,
                    lower_bound=0.1,
                    upper_bound=1.9,
                    descr="Tension variable fourth segment end",
                ),
            ],
            frozen=True,
        )
        variables.adjust_variables(var_dict, strict_bounds=False)
        super().__init__(variables)

    def create_shape(self, label=""):
        """
        Make a CAD representation of the poly spline.

        Parameters
        ----------
        label: str, default = ""
            Label to give the wire

        Returns
        -------
        shape: BluemiraWire
            CAD Wire of the geometry
        """
        variables = self.variables.values
        (
            x1,
            x2,
            z2,
            height,
            top,
            upper,
            dz,
            flat,
            tilt,
            bottom,
            lower,
        ) = variables[:11]
        l_start = variables[11:15]
        l_end = variables[15:]

        tilt = np.deg2rad(tilt)
        height = 0.5 * height
        ds_z = flat * height * np.cos(tilt)
        ds_x = flat * height * np.sin(tilt)

        # Vertices
        x = [x1, x1 + top * (x2 - x1), x2 + ds_x, x2 - ds_x, x1 + bottom * (x2 - x1), x1]
        z = [
            upper * height + dz,
            height + dz,
            z2 * height + ds_z + dz,
            z2 * height - ds_z + dz,
            -height + dz,
            -lower * height + dz,
        ]
        theta = [
            0.5 * np.pi,
            0,
            -0.5 * np.pi - tilt,
            -0.5 * np.pi - tilt,
            -np.pi,
            0.5 * np.pi,
        ]

        wires = []
        for i, j in zip([0, 1, 2, 3], [0, 1, 3, 4]):
            k = j + 1
            p0 = [x[j], 0, z[j]]
            p3 = [x[k], 0, z[k]]
            p1, p2 = self._make_control_points(
                p0, p3, theta[j], theta[k] - np.pi, l_start[i], l_end[i]
            )
            wires.append(make_bezier([p0, p1, p2, p3], label=f"segment_{i}"))

        if flat != 0:
            outer_straight = make_polygon(
                [[x[2], 0, z[2]], [x[3], 0, z[3]]], label="outer_straight"
            )
            wires.insert(2, outer_straight)

        straight_segment = wire_closure(BluemiraWire(wires), label="inner_straight")
        wires.append(straight_segment)

        return BluemiraWire(wires, label=label)

    @staticmethod
    def _make_control_points(p0, p3, theta0, theta3, l_start, l_end):
        """
        Make 2 Bézier spline control points between two vertices.
        """
        dl = distance_between_points(p0, p3)

        p1, p2 = np.zeros(3), np.zeros(3)
        for point, control_point, angle, tension in zip(
            [p0, p3], [p1, p2], [theta0, theta3], [l_start, l_end]
        ):
            d_tension = 0.5 * dl * tension
            control_point[0] = point[0] + d_tension * np.cos(angle)
            control_point[2] = point[2] + d_tension * np.sin(angle)

        return p1, p2


class PictureFrameTools:
    """
    Tools Class containing methods to produce various PictureFrame variant limbs.

    """

    @staticmethod
    def _make_domed_leg(
        x_out: float,
        x_curve_start: float,
        x_mid: float,
        z_top: float,
        z_mid: float,
        r_c: float,
        axis: Iterable[float] = (0, -1, 0),
        flip: bool = False,
    ):
        """
        Makes smooth dome for CP coils. This includes a initial straight section
        and a main curved dome section, with a transitioning 'joint' between them,
        producing smooth tangent curves.

        Parameters
        ----------
        x_out: float
            Radial position of outer edge of limb [m]
        x_curve start: float
            Radial position of straight-curve transition of limb [m]
        x_mid: float
            Radial position of inner edge of  upper/lower limb [m]
        z_top: float
            Vertical position of top of limb dome [m]
        z_mid: float
            Vertical position of flat section [m]
        r_c: float
            Radius of corner transition. Nominally 0 [m]
        axis: Iterable[float]
            [x,y,z] vector normal to plane of parameterisation
        flip: bool
            True if limb is lower limb of section, False if upper

        Returns
        -------
        shape: BluemiraWire
            CAD Wire of the geometry
        """
        # Define the basic main curve (with no joint or transitions curves)
        alpha = np.arctan(0.5 * (x_out - x_curve_start) / abs(z_top - z_mid))
        theta_leg_basic = 2 * (np.pi - 2 * alpha)
        r_leg = 0.5 * (x_out - x_curve_start) / np.sin(theta_leg_basic * 0.5)

        # Transitioning Curves
        sin_a = np.sin(theta_leg_basic * 0.5)
        cos_a = np.cos(theta_leg_basic * 0.5)

        # Joint Curve
        r_j = min(x_curve_start - x_mid, 0.8)
        theta_j = np.arccos((r_leg * cos_a + r_j) / (r_leg + r_j))
        deg_theta_j = np.rad2deg(theta_j)

        # Corner Transitioning Curve
        theta_trans = np.arccos((r_j - r_leg * sin_a) / (r_j - r_leg))
        deg_theta_trans = np.rad2deg(theta_trans)

        # Main leg curve angle
        leg_angle = 90 + deg_theta_j

        # Labels
        if flip:
            label = "bottom"
            z_top_r_leg = z_top + r_leg
            z_mid_r_j = z_mid - r_j
            z_trans_diff = -(r_leg - r_j)
            z_corner = z_mid + r_c
            corner_angle_s = 90
            corner_angle_e = 180
            joint_angle_s = 90 - deg_theta_j
            joint_angle_e = 90
            leg_angle_s = tc_angle_e = deg_theta_trans
            leg_angle_e = leg_angle
            tc_angle_s = 0
            ind = slice(None, None, -1)
        else:
            label = "top"
            z_top_r_leg = z_top - r_leg
            z_mid_r_j = z_mid + r_j
            z_trans_diff = r_leg - r_j
            z_corner = z_mid - r_c
            corner_angle_s = 180
            corner_angle_e = 270
            joint_angle_s = -90
            joint_angle_e = deg_theta_j - 90
            leg_angle_s = -leg_angle
            leg_angle_e = tc_angle_s = -deg_theta_trans
            tc_angle_e = 0
            ind = slice(None)

        # Basic main curve centre
        leg_centre = (x_out - 0.5 * (x_out - x_curve_start), 0, z_top_r_leg)

        # Joint curve centre
        joint_curve_centre = (
            leg_centre[0] - (r_leg + r_j) * np.sin(theta_j),
            0,
            z_mid_r_j,
        )

        # Transition curve centre
        x_trans = leg_centre[0] + (r_leg - r_j) * np.cos(theta_trans)
        z_trans = leg_centre[2] + z_trans_diff * np.sin(theta_trans)

        # Inner Corner
        corner_in = make_circle(
            r_c,
            [x_mid + r_c, 0.0, z_corner],
            start_angle=corner_angle_s,
            end_angle=corner_angle_e,
            axis=[0, 1, 0],
            label=f"inner_{label}_corner",
        )

        # Build straight section of leg
        p1 = [x_mid + r_c, 0, z_mid]
        p2 = [leg_centre[0] - (r_leg + r_j) * np.sin(theta_j), 0, z_mid]
        straight_section = make_polygon([p2, p1] if flip else [p1, p2])

        # Dome-inboard section transition curve
        joint_curve = make_circle(
            radius=r_j,
            center=joint_curve_centre,
            start_angle=joint_angle_s,
            end_angle=joint_angle_e,
            axis=axis,
            label=f"{label}_limb_joint",
        )

        # Main leg curve
        leg_curve = make_circle(
            radius=r_leg,
            center=leg_centre,
            start_angle=leg_angle_s,
            end_angle=leg_angle_e,
            axis=[0, 1, 0],
            label=f"{label}_limb_dome",
        )

        # Outboard corner transition curve
        transition_curve = make_circle(
            radius=r_j,
            center=[x_trans, 0, z_trans],
            start_angle=tc_angle_s,
            end_angle=tc_angle_e,
            axis=[0, 1, 0],
            label=f"{label}_limb_corner",
        )

        return BluemiraWire(
            [corner_in, straight_section, joint_curve, leg_curve, transition_curve][ind],
            label=f"{label}_limb",
        )

    @staticmethod
    def _make_flat_leg(
        x_in: float,
        x_out: float,
        z: float,
        r_i: float,
        r_o: float,
        axis: Iterable[float] = (0, 1, 0),
        flip: bool = False,
    ):
        """
        Makes a flat leg (top/bottom limb) with the option of one end rounded.

        Parameters
        ----------
        x_in: float
            Radial position of inner edge of limb [m]
        x_out: float
            Radial position of outer edge of limb [m]
        z: float
            Vertical position of limb [m]
        r_i: float
            Radius of inner corner [m]
        r_o: float
            Radius of outer corner [m]
        axis: Iterable[float]
            [x,y,z] vector normal to plane of parameterisation
        flip: bool
            True if limb is lower limb of section, False if upper

        Returns
        -------
        shape: BluemiraWire
            CAD Wire of the geometry
        """
        wires = []
        label = "bottom" if flip else "top"

        # Set corner radius centres
        c_i = [x_in + r_i, 0.0, z + r_i if flip else z - r_i]
        c_o = [x_out - r_o, 0.0, z + r_o if flip else z - r_o]

        # Inner Corner
        if r_i != 0.0:
            wires.append(
                make_circle(
                    r_i,
                    c_i,
                    start_angle=90 if flip else 180,
                    end_angle=180 if flip else 270,
                    axis=axis,
                    label=f"inner_{label}_corner",
                )
            )
        # Straight Section
        p1 = [x_in + r_i, 0.0, z]
        p2 = [x_out - r_o, 0.0, z]
        wires.append(make_polygon([p2, p1] if flip else [p1, p2], label=f"{label}_limb"))

        # Outer corner
        if r_o != 0.0:

            wires.append(
                make_circle(
                    r_o,
                    c_o,
                    start_angle=0 if flip else 270,
                    end_angle=90 if flip else 0,
                    axis=axis,
                    label=f"outer_{label}_corner",
                )
            )

        if flip:
            wires.reverse()

        return BluemiraWire(wires, label=f"{label}_limb")

    @staticmethod
    def _make_tapered_inner_leg(
        x_in: float,
        x_mid: float,
        z_in: float,
        z1: float,
        z2: float,
        axis: Iterable[float] = (0, 1, 0),
    ):
        """
        Makes a tapered inboard leg using a circle arc taper, symmetric about the
        midplane with the tapering beginning at a certain height and reaching a
        maximum taper at the midplane.

        Parameters
        ----------
        x_in: float
            Radial position of innermost point of limb [m]
        x_mid: float
            Radial position of outer edge of limb [m]
        z_in: float
            Vertical position of start of tapering [m]
        z1: float
            Vertical position of top of limb [m]
        z2: float
            Vertical position of bottom of limb [m]
        axis: Iterable[float]
            [x,y,z] vector normal to plane of parameterisation

        Returns
        -------
        shape: BluemiraWire
            CAD Wire of the geometry
        """
        # Bottom straight section
        p1 = [x_mid, 0, -z_in]
        p2 = [x_mid, 0, z2]
        bot_straight = make_polygon([p2, p1], label="inner_limb_mid_down")

        # Curved taper radius
        x_t = x_mid - x_in
        alpha = np.arctan(z_in / (x_t))
        theta_t = np.pi - 2 * alpha
        r_taper = z_in / np.sin(theta_t)

        # Curved taper angle
        angle = np.rad2deg(np.arcsin(z_in / r_taper))
        ct_angle = make_circle(
            radius=r_taper,
            center=(x_in + r_taper, 0, 0),
            start_angle=180 - angle,
            end_angle=180 + angle,
            axis=axis,
            label="inner_limb",
        )

        # Top straight section
        p3 = [x_mid, 0, z_in]
        p4 = [x_mid, 0, z1]
        top_straight = make_polygon([p3, p4], label="inner_limb_mid_up")

        return BluemiraWire([bot_straight, ct_angle, top_straight], label="inner_limb")

    def _connect_curve_to_outer_limb(self, top, bottom):

        return self._outer_limb(
            top.discretize(100, byedges=True)[:, -1],
            bottom.discretize(100, byedges=True)[:, 0],
        )

    def _connect_straight_to_outer_limb(self, top, bottom):
        return self._outer_limb(top, bottom)

    def _connect_straight_to_inner_limb(self, top, bottom):
        return self._inner_limb(top, bottom)

    @staticmethod
    def _inner_limb(p1, p2):
        return make_polygon([p1, p2], label="inner_limb")

    @staticmethod
    def _outer_limb(p1, p2):
        return make_polygon([p1, p2], label="outer_limb")


class PFrameSection(Enum):
    """
    Picture Frame sections
    """

    CURVED = partial(PictureFrameTools._make_domed_leg)
    FLAT = partial(PictureFrameTools._make_flat_leg)
    TAPERED_INNER = partial(PictureFrameTools._make_tapered_inner_leg)

    def __call__(self, *args, **kwargs):
        return self.value(*args, **kwargs)


class PictureFrameMeta(type(GeometryParameterisation), type(PictureFrameTools)):

    __SECT_STR = Union[str, PFrameSection]

    def __call__(
        cls,  # noqa: N805
        var_dict: Optional[Dict] = None,
        *,
        upper: __SECT_STR = PFrameSection.FLAT,
        lower: __SECT_STR = PFrameSection.FLAT,
        inner: Optional[__SECT_STR] = None,
    ):
        cls.upper = upper if isinstance(upper, PFrameSection) else PFrameSection[upper]
        cls.lower = lower if isinstance(lower, PFrameSection) else PFrameSection[lower]

        if isinstance(inner, str):
            cls.inner = PFrameSection[inner]
            cls.inner_vars = lambda self, v: (v.x1, v.x3, v.z3, v.z1 - v.ri, v.z2 + v.ri)
        elif inner is None:
            cls.inner = cls._connect_straight_to_inner_limb
            if PFrameSection.CURVED in [cls.upper, cls.lower]:
                cls.inner_vars = lambda self, v: (
                    [v.x1, 0, v.z2 + v.r_c],
                    [v.x1, 0, v.z1 - v.r_c],
                )
            else:
                cls.inner_vars = lambda self, v: (
                    [v.x1, 0, v.z2 + v.ri],
                    [v.x1, 0, v.z1 - v.ri],
                )

        if (
            isinstance(cls.inner, PFrameSection)
            and cls.inner != PFrameSection.TAPERED_INNER
        ):
            raise ValueError(f"The inner leg cannot be {cls.inner}")

        if cls.upper == PFrameSection.CURVED:
            cls.upper_vars = lambda self, v: (
                v.x2,
                v.x_curve_start,
                v.x1,
                v.z1_peak,
                v.z1,
                v.r_c,
            )
        elif cls.upper == PFrameSection.FLAT:
            if cls.lower == PFrameSection.CURVED:
                cls.upper_vars = lambda self, v: (v.x1, v.x2, v.z1, v.r_c, v.r_c)
            elif cls.inner == PFrameSection.TAPERED_INNER:
                cls.upper_vars = lambda self, v: (v.x3, v.x2, v.z1, v.ri, v.ro)
            else:
                cls.upper_vars = lambda self, v: (v.x1, v.x2, v.z1, v.ri, v.ro)

        else:
            raise ValueError(f"The upper leg cannot be {cls.upper}")

        if cls.lower == PFrameSection.CURVED:
            cls.lower_vars = lambda self, v: (
                v.x2,
                v.x_curve_start,
                v.x1,
                v.z2_peak,
                v.z2,
                v.r_c,
            )
        elif cls.lower == PFrameSection.FLAT:
            if cls.upper == PFrameSection.CURVED:
                cls.lower_vars = lambda self, v: (v.x1, v.x2, v.z2, v.r_c, v.r_c)
            elif cls.inner == PFrameSection.TAPERED_INNER:
                cls.lower_vars = lambda self, v: (v.x3, v.x2, v.z2, v.ri, v.ro)
            else:
                cls.lower_vars = lambda self, v: (v.x1, v.x2, v.z2, v.ri, v.ro)
        else:
            raise ValueError(f"The lower leg cannot be {cls.lower}")

        if PFrameSection.CURVED in [cls.upper, cls.lower]:
            cls.outer = cls._connect_curve_to_outer_limb
            cls.outer_vars = lambda self, top_leg, bot_leg, v: (top_leg, bot_leg)
        else:
            cls.outer = cls._connect_straight_to_outer_limb
            cls.outer_vars = lambda self, top_leg, bot_leg, v: (
                [v.x2, 0, v.z1 - v.ro],
                [v.x2, 0, v.z2 + v.ro],
            )

        obj = cls.__new__(cls)
        obj.__init__(var_dict)
        return obj


class PictureFrame(
    GeometryParameterisation, PictureFrameTools, metaclass=PictureFrameMeta
):
    """
    Picture-frame geometry parameterisation.

    Parameters
    ----------
    var_dict: Optional[dict]
        Dictionary with which to update the default values of the parameterisation.

    Notes
    -----
    The base dictionary keys in var_dict are:

    x1: float
        Radial position of inner edge of upper/lower limb [m]
    x2: float
        Radial position of outer limb [m]
    z1: float
        Vertical position of top limb [m]
    z2: float
        Vertical position of top limb [m]
    ri: float
        Radius of inner corners [m]
    ro: float
        Radius of outer corners [m]

    For curved pictures frames there is no 'ri' or 'ro' but the additional keys are:

    z1_peak: float
        Vertical position of top of limb dome [m]
    z2_peak: float
        Vertical position of top of limb dome [m]
    r_c: float
        radius of inboard and outboard corners. [m]

    For tapered inner leg the additional keys are:

    x3: float
        Radial position of outer limb [m]
    z3: float
        Vertical position of top of tapered section [m]
    """

    __slots__ = tuple(
        [
            f"{leg}{var}"
            for leg in ["inner", "upper", "lower", "outer"]
            for var in ["", "_vars"]
        ]
    )

    def __init__(self, var_dict=None):
        bounded_vars = [
            BoundedVariable(
                "x1", 0.4, lower_bound=0.3, upper_bound=0.5, descr="Inner limb radius"
            ),
            BoundedVariable(
                "x2", 9.5, lower_bound=9.4, upper_bound=9.8, descr="Outer limb radius"
            ),
            BoundedVariable(
                "z1", 9.5, lower_bound=8, upper_bound=10.5, descr="Upper limb height"
            ),
            BoundedVariable(
                "z2", -9.5, lower_bound=-10.5, upper_bound=-8, descr="Lower limb height"
            ),
        ]

        if PFrameSection.CURVED in [self.upper, self.lower]:
            bounded_vars += [
                BoundedVariable(
                    "x_curve_start",
                    2.5,
                    lower_bound=2.4,
                    upper_bound=2.6,
                    descr="Curve start radius",
                ),
                BoundedVariable(
                    "z1_peak",
                    11,
                    lower_bound=6,
                    upper_bound=12,
                    descr="Upper limb curve height",
                ),
                BoundedVariable(
                    "z2_peak",
                    -11,
                    lower_bound=-12,
                    upper_bound=-6,
                    descr="Lower limb curve height",
                ),
                BoundedVariable(
                    "r_c",
                    0.1,
                    lower_bound=0.09,
                    upper_bound=0.11,
                    descr="Corner/transition joint radius",
                ),
            ]
        else:
            bounded_vars += [
                BoundedVariable(
                    "ri",
                    1,
                    lower_bound=0,
                    upper_bound=2,
                    descr="Inboard corner radius",
                ),
                BoundedVariable(
                    "ro", 2, lower_bound=1, upper_bound=5, descr="Outboard corner radius"
                ),
            ]

            if self.inner == PFrameSection.TAPERED_INNER:
                bounded_vars += [
                    BoundedVariable(
                        "x3",
                        1.1,
                        lower_bound=1,
                        upper_bound=1.3,
                        descr="Middle limb radius",
                    ),
                    BoundedVariable(
                        "z3",
                        6.5,
                        lower_bound=6,
                        upper_bound=8,
                        descr="Taper angle stop height",
                    ),
                ]

        variables = OptVariables(bounded_vars, frozen=True)
        variables.adjust_variables(var_dict, strict_bounds=False)
        super().__init__(variables)

    def create_shape(self, label=""):
        """
        Make a CAD representation of the picture frame.

        Parameters
        ----------
        label: str, default = ""
            Label to give the wire

        Returns
        -------
        shape: BluemiraWire
            CAD Wire of the Picture Frame geometry
        """
        inb_leg = self.inner(*self.inner_vars(self.variables))
        top_leg = self.upper(*self.upper_vars(self.variables), flip=False)
        bot_leg = self.lower(*self.lower_vars(self.variables), flip=True)
        out_leg = self.outer(*self.outer_vars(top_leg, bot_leg, self.variables))

        return BluemiraWire([inb_leg, top_leg, out_leg, bot_leg], label=label)
