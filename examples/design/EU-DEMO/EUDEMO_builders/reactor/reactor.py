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

import os
from typing import Dict, TypeVar

from bluemira.base.designer import run_designer
from bluemira.base.parameter_frame import NewParameterFrame as ParameterFrame
from bluemira.base.parameter_frame import make_parameter_frame
from EUDEMO_builders.equilibria import EquilibriumDesigner
from EUDEMO_builders.ivc import design_ivc
from EUDEMO_builders.reactor.params import EUDEMOReactorParams

ROOT_DIR = os.path.dirname(__file__)
PARAMS_FILE = os.path.join(ROOT_DIR, "params.json")

_PfT = TypeVar("_PfT", bound=ParameterFrame)


def radial_build(params: _PfT, build_config: Dict) -> _PfT:
    """
    Update parameters after a radial build is run.

    Usual this would run an external code like PROCESS, but we'll just
    read in a previous PROCESS run, as the PROCESS solver hasn't yet
    been made to work with the new ParameterFrame.
    """
    import json

    with open(os.path.join(ROOT_DIR, "mockPROCESS.json"), "r") as f:
        param_values = json.load(f)
    params.update_values(param_values, source="PROCESS (mock)")
    return params


def build(params: EUDEMOReactorParams, build_config: Dict):
    params = radial_build(params, build_config["Radial Build"])


def design_ivc_components(params, build_config):
    return


if __name__ == "__main__":
    params = make_parameter_frame(PARAMS_FILE, EUDEMOReactorParams)
    if params is None:
        raise ValueError("Params cannot be None")
    build_config = {
        "Radial build": {},
        "Equilibrium": {
            "plot_optimisation": False,
            "run_mode": "run",
            "file_path": "/home/bf2936/bluemira/code/bluemira/examples/design/EU-DEMO/EUDEMO_builders/reactor/equlibrium_eqdsk.json",
        },
        "IVC": {
            "Wall silhouette": {
                "param_class": "EUDEMO_builders.ivc.wall_silhouette_parameterisation::WallPolySpline",
                "variables_map": {
                    "x1": {  # ib radius
                        "value": "r_fw_ib_in",
                    },
                    "x2": {  # ob radius
                        "value": "r_fw_ob_in",
                    },
                },
                "run_mode": "mock",
                "name": "First Wall",
                "problem_class": "bluemira.geometry.optimisation::MinimiseLengthGOP",
            },
            "Divertor silhouette": {},
        },
    }

    params = radial_build(params, build_config["Radial build"])
    eq = run_designer(EquilibriumDesigner, params, build_config["Equilibrium"])
    ivc_boundary, plasma_face, ivc_boundary = design_ivc(
        params, build_config["IVC"], equilibrium=eq
    )
