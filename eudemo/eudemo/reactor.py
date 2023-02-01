# bluemira is an integrated inter-disciplinary design tool for future fusion
# reactors. It incorporates several modules, some of which rely on other
# codes, to carry out a range of typical conceptual fusion reactor design
# activities.
#
# Copyright (C) 2021-2023 M. Coleman, J. Cook, F. Franza, I.A. Maione, S. McIntosh,
#                         J. Morris, D. Short
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
9. Build cryostat
10. Build radiation shield
11. Produce power cycle report
"""

import json
import os
from pathlib import Path
from typing import Dict

from bluemira.base.components import Component
from bluemira.base.designer import run_designer
from bluemira.base.look_and_feel import bluemira_warn
from bluemira.base.parameter_frame import make_parameter_frame
from bluemira.base.reactor import Reactor
from bluemira.builders.cryostat import CryostatBuilder, CryostatDesigner
from bluemira.builders.divertor import DivertorBuilder
from bluemira.builders.pf_coil import PFCoilBuilder, PFCoilPictureFrame
from bluemira.builders.plasma import Plasma, PlasmaBuilder
from bluemira.builders.radiation_shield import (
    RadiationShieldBuilder,
    RadiationShieldDesigner,
)
from bluemira.builders.thermal_shield import CryostatTSBuilder, VVTSBuilder
from bluemira.equilibria.equilibrium import Equilibrium
from bluemira.geometry.tools import make_polygon
from eudemo.blanket import Blanket, BlanketBuilder
from eudemo.equilibria import EquilibriumDesigner
from eudemo.ivc import design_ivc
from eudemo.ivc.divertor_silhouette import Divertor
from eudemo.params import EUDEMOReactorParams
from eudemo.pf_coils import PFCoil, PFCoilsDesigner
from eudemo.power_cycle import SteadyStatePowerCycleSolver
from eudemo.radial_build import radial_build
from eudemo.tf_coils import TFCoil, TFCoilBuilder, TFCoilDesigner
from eudemo.thermal_shield import (
    CryostatThermalShield,
    RadiationShield,
    VacuumVesselThermalShield,
)
from eudemo.vacuum_vessel import VacuumVessel, VacuumVesselBuilder

CONFIG_DIR = Path(__file__).parent.parent / "config"
PARAMS_FILE = os.path.join(CONFIG_DIR, "params.json")


class EUDEMO(Reactor):
    """EUDEMO reactor definition."""

    plasma: Plasma
    vacuum_vessel: VacuumVessel
    divertor: Divertor
    blanket: Blanket
    tf_coils: TFCoil
    vv_thermal: VacuumVesselThermalShield
    pf_coils: PFCoil
    cryostat: Cryostat
    cryostat_thermal: CryostatThermalShield
    radiation_shield: RadiationShield


def build_plasma(build_config: Dict, eq: Equilibrium) -> Plasma:
    """Build EUDEMO plasma from an equilibrium."""
    lcfs_loop = eq.get_LCFS()
    lcfs_wire = make_polygon({"x": lcfs_loop.x, "z": lcfs_loop.z}, closed=True)
    builder = PlasmaBuilder(build_config, lcfs_wire)
    return Plasma(builder.build())


def build_vacuum_vessel(params, build_config, ivc_koz) -> VacuumVessel:
    """Build the vacuum vessel around the given IVC keep-out zone."""
    vv_builder = VacuumVesselBuilder(params, build_config, ivc_koz)
    return VacuumVessel(vv_builder.build())


def build_divertor(params, build_config, div_silhouette) -> Divertor:
    """Build the divertor given a silhouette of a sector."""
    builder = DivertorBuilder(params, build_config, div_silhouette)
    return Divertor(builder.build())


def build_blanket(params, build_config, blanket_face) -> Blanket:
    """Build the blanket given a silhouette of a sector."""
    builder = BlanketBuilder(params, build_config, blanket_face)
    return Blanket(builder.build())


def build_vvts(params, build_config, vv_boundary):
    """Build the vacuum vessel thermal shield"""
    vv_thermal_shield = VVTSBuilder(
        params,
        build_config.get("Vacuum vessel", {}),
        keep_out_zone=vv_boundary,
    )
    return VacuumVesselThermalShield(vv_thermal_shield.build())


def build_tf_coils(
    params, build_config, separatrix, vacuum_vessel_cross_section
) -> TFCoil:
    """Design and build the TF coils for the reactor."""
    centreline, wp_cross_section = run_designer(
        TFCoilDesigner,
        params,
        build_config,
        separatrix=separatrix,
        keep_out_zone=vacuum_vessel_cross_section,
    )
    builder = TFCoilBuilder(
        params, build_config, centreline.create_shape(), wp_cross_section
    )
    return TFCoil(builder.build(), builder._make_field_solver())


def build_pf_coils(params, build_config, tf_coil_boundary, pf_coil_keep_out_zones=()):
    """
    Design and build the PF coils for the reactor.
    """
    pf_designer = PFCoilsDesigner(
        params,
        build_config,
        tf_coil_boundary,
        pf_coil_keep_out_zones,
    )
    coilset = pf_designer.execute()

    wires = []
    for name in coilset.name:
        if not (coilset[name].dx == 0 or coilset[name].dz == 0):
            wires.append(
                (PFCoilPictureFrame(params, coilset[name]), coilset[name].ctype)
            )
        else:
            bluemira_warn(f"Coil {name} has no size")

    builders = []
    for (des, ctype) in wires:
        tk_ins = (
            params.tk_pf_insulation if ctype.name == "PF" else params.tk_cs_insulation
        )
        tk_case = params.tk_pf_casing if ctype.name == "PF" else params.tk_cs_casing
        builders.append(
            PFCoilBuilder(
                {
                    "tk_insulation": {"value": tk_ins.value, "unit": "m"},
                    "tk_casing": {"value": tk_case.value, "unit": "m"},
                    "ctype": {"value": ctype.name, "unit": ""},
                },
                build_config,
                des.execute(),
            )
        )

    return PFCoil(
        Component("PF Coils", children=[builder.build() for builder in builders]),
        coilset,
    )


def build_cryots(params, build_config, pf_kozs, tf_koz):
    cryoTSb = CryostatTSBuilder(
        params,
        build_config.get("Cryostat", {}),
        reactor.pf_coils.xz_boundary(),
        reactor.tf_coils.boundary(),
    )
    return CryostatThermalShield(cryoTSb.build())


def build_cryostat(params, build_config, cryostat_thermal_koz):
    cryod = CryostatDesigner(
        params,
        reactor.cryostat_thermal.get_component("xz").get_component_properties(
            "shape", first=False
        )[0],
    )
    cryob = CryostatBuilder(params, build_config, cryod)
    return Cryostat(cryob.build())


def build_radiation_shield(params, build_config, cryostat_koz):
    radshieldd = RadiationShieldDesigner(
        reactor.cryostat.get_component("xz").get_component_properties(
            "shape", first=False
        )[0]
    )
    radshieldb = RadiationShieldBuilder(params, build_config, radshieldd)
    return RadiationShield(radshieldb.build())


def _read_json(file_path: str) -> Dict:
    """Read a JSON file to a dictionary."""
    with open(file_path, "r") as f:
        return json.load(f)


if __name__ == "__main__":
    reactor = EUDEMO("EUDEMO")
    params = make_parameter_frame(PARAMS_FILE, EUDEMOReactorParams)
    if params is None:
        raise ValueError("Params cannot be None")
    build_config = _read_json(os.path.join(CONFIG_DIR, "build_config.json"))

    params = radial_build(params, build_config["Radial build"])

    eq = run_designer(EquilibriumDesigner, params, build_config["Equilibrium"])

    reactor.plasma = build_plasma(build_config.get("Plasma", {}), eq)

    blanket_face, divertor_face, ivc_boundary = design_ivc(
        params, build_config["IVC"], equilibrium=eq
    )

    reactor.vacuum_vessel = build_vacuum_vessel(
        params, build_config.get("Vacuum vessel", {}), ivc_boundary
    )
    reactor.divertor = build_divertor(
        params, build_config.get("Divertor", {}), divertor_face
    )
    reactor.blanket = build_blanket(
        params, build_config.get("Blanket", {}), blanket_face
    )

    reactor.vv_thermal = build_vvts(
        params,
        build_config.get("Thermal shield", {}),
        reactor.vacuum_vessel.xz_boundary(),
    )

    reactor.tf_coils = build_tf_coils(
        params,
        build_config.get("TF coils", {}),
        reactor.plasma.lcfs(),
        reactor.vacuum_vessel.xz_boundary(),
    )

    reactor.pf_coils = build_pf_coils(
        params,
        build_config.get("PF coils", {}),
        reactor.tf_coils.boundary(),
        pf_coil_keep_out_zones=[],
    )

    reactor.cryostat_thermal = build_cryots(
        params,
        build_config.get("Thermal shield", {}),
        reactor.pf_coils.xz_boundary(),
        reactor.tf_coils.boundary(),
    )

    reactor.cryostat = build_cryostat(
        params, build_config.get("Cryostat", {}), reactor.cryostat_thermal.xz_boundary()
    )

    reactor.radiation_shield = build_radiation_shield(
        params, build_config, reactor.cryostat.xz_boundary()
    )

    sspc_solver = SteadyStatePowerCycleSolver(params)
    sspc_result = sspc_solver.execute()
    sspc_solver.model.plot()

    reactor.show_cad()
