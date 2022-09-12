# bluemira is an integrated inter-disciplinary design tool for future fusion
# reactors. It incorporates several modules, some of which rely on other
# codes, to carry out a range of typical conceptual fusion reactor design
# activities.
#
# Copyright (C) 2022 M. Coleman, J. Cook, F. Franza, I.A. Maione, S. McIntosh, J. Morris,
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
The EUDEMO reactor design routine.

1. Radial build (using PROCESS)
2. Perform equilibria optimisation
3. Build plasma
4. Design scaffold for the IVCs
5. Build vacuum vessel
6. Build TF coils
7. Build PF coils
8. Build cryo thermal shield
9. Build cyostat
10. Build radiation shield
11. Produce power cycle report
"""

import json
import os
from typing import Dict, Type

from bluemira.base.builder import ComponentManager
from bluemira.base.components import Component
from bluemira.base.designer import run_designer
from bluemira.base.parameter_frame import make_parameter_frame
from bluemira.builders.divertor import Divertor, DivertorBuilder
from bluemira.builders.plasma import Plasma, PlasmaBuilder
from bluemira.display.displayer import ComponentDisplayer
from bluemira.equilibria.equilibrium import Equilibrium
from bluemira.geometry.tools import make_polygon
from EUDEMO_builders.equilibria import EquilibriumDesigner
from EUDEMO_builders.ivc import design_ivc
from EUDEMO_builders.radial_build import radial_build
from EUDEMO_builders.reactor.params import EUDEMOReactorParams
from EUDEMO_builders.vacuum_vessel import VacuumVessel, VacuumVesselBuilder

ROOT_DIR = os.path.dirname(__file__)
PARAMS_FILE = os.path.join(ROOT_DIR, "params.json")


def _read_json(file_path: str) -> Dict:
    """Read a JSON file to a dictionary."""
    with open(file_path, "r") as f:
        return json.load(f)


def build_plasma(build_config: Dict, eq: Equilibrium) -> Plasma:
    """Build EUDEMO plasma from an equilibrium."""
    lcfs_loop = eq.get_LCFS()
    lcfs_wire = make_polygon({"x": lcfs_loop.x, "z": lcfs_loop.z}, closed=True)
    builder = PlasmaBuilder(build_config, lcfs_wire)
    return builder.build()


def build_vacuum_vessel(params, build_config, ivc_koz) -> VacuumVessel:
    """Build the vacuum vessel around the given IVC keep-out zone."""
    vv_builder = VacuumVesselBuilder(params, build_config, ivc_koz)
    return vv_builder.build()


def build_divertor(params, build_config, div_silhouette) -> Divertor:
    """Build the divertor given a silhouette of a sector."""
    builder = DivertorBuilder(params, build_config, div_silhouette)
    return builder.build()


class ReactorError(Exception):
    """Exceptions related to reactors."""


class EUDEMO:
    """EUDEMO reactor definition."""

    plasma: Plasma
    vacuum_vessel: VacuumVessel
    divertor: Divertor

    def __init__(self, name: str):
        self.name = name

    def component(self) -> Component:
        """Return the component tree."""
        component = Component(self.name)
        comp_type: Type
        for comp_name, comp_type in self.__annotations__.items():
            if not issubclass(comp_type, ComponentManager):
                continue
            try:
                component_manager = getattr(self, comp_name)
            except AttributeError:
                # raise ReactorError(f"Component not set for '{comp_name}'.")
                continue

            component.add_child(component_manager.component())
        return component

    def show_cad(self, dim="xyz", **kwargs):
        """Show the CAD build of the reactor."""
        comp = self.component()
        ComponentDisplayer().show_cad(comp.get_component(dim, first=False), **kwargs)


if __name__ == "__main__":
    reactor = EUDEMO("EUDEMO")
    params = make_parameter_frame(PARAMS_FILE, EUDEMOReactorParams)
    if params is None:
        raise ValueError("Params cannot be None")
    build_config = _read_json(os.path.join(ROOT_DIR, "build_config.json"))

    params = radial_build(params, build_config["Radial build"])

    eq = run_designer(EquilibriumDesigner, params, build_config["Equilibrium"])

    reactor.plasma = build_plasma(build_config.get("Plasma", {}), eq)

    blanket_face, divertor_face, ivc_boundary = design_ivc(
        params, build_config["IVC"], equilibrium=eq
    )

    # Do not add VV to the reactor, as the built shape
    vacuum_vessel = build_vacuum_vessel(
        params, build_config.get("Vacuum vessel", {}), ivc_boundary
    )
    reactor.divertor = build_divertor(
        params, build_config.get("Divertor", {}), divertor_face
    )

    reactor.show_cad()
