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
Base ``DesignStage`` class for reactor builds.
"""

import abc
import enum
from typing import Type

from bluemira.base.components import Component, PhysicalComponent
from bluemira.base.parameter import ParameterFrame
from bluemira.base.solver import RunMode, SolverABC, Task
from bluemira.display.displayer import show_cad
from bluemira.display.plotter import plot_2d
from bluemira.geometry.face import BluemiraFace
from bluemira.geometry.tools import revolve_shape
from bluemira.geometry.wire import BluemiraWire


class DesignRunMode(RunMode):
    RUN = enum.auto()
    MOCK = enum.auto()
    READ = enum.auto()


class DesignSetup(Task):
    """
    Performs setup for a ``DesignStage``.

    This setup will perform generic parameter parsing and checking.
    """

    def run(self):
        return self.params

    # No mock/read required, as the inputs have no impact on the output?
    # Or do we just call .run() from each?


class DesignBuilder(Task):
    """
    Build the result of a design.

    Create the ``build_xz``, ``build_xy``, and/or ``build_xyz`` methods,
    to define the build in the respective dimensions.
    """

    @abc.abstractproperty
    def name(self) -> str:
        pass

    def build_xz(self, *args) -> Component:
        pass

    def build_xy(self, *args) -> Component:
        pass

    def build_xyz(self, *args) -> Component:
        pass

    def run(self, *args) -> Component:
        component = Component(self.name)
        if xz := self.build_xz(*args):
            component.add_child(Component("xz", children=(xz,)))
        if xy := self.build_xy(*args):
            component.add_child(Component("xy", children=(xy,)))
        if xyz := self.build_xyz(*args):
            component.add_child(Component("xyz", children=(xyz,)))
        return component

    def mock(self, *args) -> Component:
        return self.run(*args)

    def read(self, *args) -> Component:
        return self.run(*args)


class DesignStage(SolverABC):
    """
    Inherit and specify class properties ``designer`` and ``builder`` to
    define a new design stage.
    """

    @abc.abstractproperty
    def designer(self) -> Type["Designer"]:
        pass

    @abc.abstractproperty
    def builder(self) -> Type[DesignBuilder]:
        pass

    @abc.abstractproperty
    def name(self) -> str:
        pass

    run_mode_cls = DesignRunMode
    setup_cls = DesignSetup
    run_cls = None
    teardown_cls = None

    def __init__(self, params: ParameterFrame):
        self.run_cls = self.designer
        self.teardown_cls = self.builder
        super().__init__(params)


if __name__ == "__main__":

    from bluemira.equilibria.shapes import JohnerLCFS

    # fmt: off
    params = ParameterFrame.from_list(
        [
            ["Name", "Reactor name", "MyExample", "dimensionless", None, "Input", None],
            ["R_0", "Major radius", 9.0, "m", None, "Input", None],

            # Plasma parameters
            ["z_0", "Reference vertical coordinate", 0.0, "m", None, "Input", None],
            ["A", "Aspect ratio", 3.1, "dimensionless", None, "Input", None],
            ["kappa_u", "Upper elongation", 1.6, "dimensionless", None, "Input", None],
            ["kappa_l", "Lower elongation", 1.8, "dimensionless", None, "Input", None],
            ["delta_u", "Upper triangularity", 0.4, "dimensionless", None, "Input", None],
            ["delta_l", "Lower triangularity", 0.4, "dimensionless", None, "Input", None],
            ["phi_u_neg", "", 0, "degree", None, "Input", None],
            ["phi_u_pos", "", 0, "degree", None, "Input", None],
            ["phi_l_neg", "", 0, "degree", None, "Input", None],
            ["phi_l_pos", "", 0, "degree", None, "Input", None],

            # TF coil parameters
            ["tf_wp_width", "Width of TF coil winding pack", 0.6, "m", None, "Input", None],
            ["tf_wp_depth", "Depth of TF coil winding pack", 0.8, "m", None, "Input", None],
        ]
    )
    # fmt: on

    class PlasmaDesigner(Task):
        def run(self, params):
            return JohnerLCFS(
                var_dict={
                    "r_0": {"value": params["R_0"]},
                    "z_0": {"value": params["z_0"]},
                    "a": {"value": params["R_0"] / params["A"]},
                }
            ).create_shape()

        def read(self):
            return self.run({"R_0": 9.0, "radius": 2.0})

        def mock(self):
            return self.run({"R_0": 9.0, "radius": 2.0})

    class PlasmaBuilder(DesignBuilder):
        name = "plasma"

        def build_xz(self, wire: BluemiraWire) -> Component:
            return PhysicalComponent("LCFS", BluemiraFace(wire))

        def build_xyz(self, wire: BluemiraWire) -> Component:
            lcfs = self.build_xz(wire).shape
            shape = revolve_shape(lcfs, degree=359)
            return PhysicalComponent("LCFS", shape)

    class PlasmaDesignStage(DesignStage):

        name = "plasma"
        designer = PlasmaDesigner
        builder = PlasmaBuilder

    plasma_stage = PlasmaDesignStage(params)
    plasma = plasma_stage.execute(DesignRunMode.RUN)

    plot_2d(plasma.get_component("xz").get_component("LCFS").shape)
    show_cad(plasma.get_component("xyz").get_component("LCFS").shape)
