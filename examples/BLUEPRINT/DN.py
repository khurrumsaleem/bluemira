# bluemira is an integrated inter-disciplinary design tool for future fusion
# reactors. It incorporates several modules, some of which rely on other
# codes, to carry out a range of typical conceptual fusion reactor design
# activities.
#
# Copyright (C) 2021 M. Coleman, J. Cook, F. Franza, I. Maione, S. McIntosh, J. Morris,
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
A typical double null tokamak fusion power reactor.
"""
import matplotlib.pyplot as plt

from BLUEPRINT.reactor import Reactor
from BLUEPRINT.systems.config import SingleNull
from BLUEPRINT.base.file import make_BP_path
from bluemira.base.look_and_feel import plot_defaults


plot_defaults()
KEY_TO_PLOT = False

REACTORNAME = "DN-DEMO"
config = {
    "Name": REACTORNAME,
    "P_el_net": 550,
    "tau_flattop": 3600,
    "plasma_type": "DN",
    "reactor_type": "Normal",
    "CS_material": "Nb3Sn",
    "PF_material": "NbTi",
    "A": 3.1,
    "n_CS": 5,
    "n_PF": 6,
    "f_ni": 0.1,
    "fw_psi_n": 1.05,
    "tk_sh_in": 0.3,
    "tk_sh_out": 0.3,
    "tk_sh_top": 0.3,
    "tk_sh_bot": 0.3,
    "tk_vv_in": 0.3,
    "tk_vv_out": 0.8,
    "tk_vv_top": 0.3,
    "tk_vv_bot": 0.3,
    "tk_ts": 0.05,
    "tk_tf_side": 0.1,
    "tk_bb_ib": 0.7,
    "tk_sol_ib": 0.225,
    "LPangle": -15,
}

build_config = {
    "generated_data_root": "!BP_ROOT!/generated_data",
    "plot_flag": False,
    "process_mode": "mock",
    "plasma_mode": "run",
    "tf_mode": "run",
    # TF coil config
    "TF_type": "D",
    "TF_objective": "L",
    "GS_type": "JT60SA",
    # FW and VV config
    "VV_parameterisation": "S",
    "FW_parameterisation": "S",
    "BB_segmentation": "radial",
    "lifecycle_mode": "life",
    "HCD_method": "power",
}

build_tweaks = {
    # TF coil optimisation tweakers (n ripple filaments)
    "nr": 1,
    "ny": 1,
    "nrippoints": 10,  # Number of points to check edge ripple on
}


class DoubleNullReactor(Reactor):
    """
    A double-null fusion power reactor class.
    """

    config: dict
    build_config: dict
    build_tweaks: dict
    default_params = SingleNull().to_records()

    def __init__(self, config, build_config, build_tweaks):
        super().__init__(config, build_config, build_tweaks)


if __name__ == "__main__":
    plt.close("all")

    LOAD = False

    if LOAD:
        filename = (
            make_BP_path(f"reactors/{REACTORNAME}", subfolder="data")
            + "/"
            + REACTORNAME
            + ".pkl"
        )
        R = DoubleNullReactor.load(filename, generated_data_root="generated_data")
    else:
        R = DoubleNullReactor(config, build_config, build_tweaks)
        R.build()
    plot_defaults()
