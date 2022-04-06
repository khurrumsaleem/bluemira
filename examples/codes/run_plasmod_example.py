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
Test for plasmod run
"""

# %%
from pprint import pprint

import matplotlib.pyplot as plt

import bluemira.codes.plasmod as plasmod
from bluemira.base.config import Configuration
from bluemira.base.logs import set_log_level

# %%[markdown]
# # Configuring the PLASMOD solver

# PLASMOD is one of the codes bluemira can use to compliment a reactor design.
# As with any of the external codes bluemira uses, a solver object is created.
# The solver object abstracts away most of the complexities of running different
# programs within bluemira.

# ## Setting up

# ### Logging
# To enable debug logging run the below cell

# %%

set_log_level("DEBUG")

# %%[markdown]
# ### Binary Location
# Firstly if plasmod is not in your system path we need to provide the
# binary location to the solver

# %%

# PLASMOD_PATH = "/home/fabrizio/bwSS/plasmod/bin/"
PLASMOD_PATH = (
    "/Users/tiago/Documents/VSCODE/BLUEMIRA/bluemira/_TIAGO_FILES_/SIMLINKS/plasmod/bin/"
)
binary = f"{PLASMOD_PATH}plasmod"

# %%[markdown]
# ### Creating the solver object
# bluemira-plasmod parameter names have been mapped across where possible.
# Some example parameters have been set here in `new_params`
# before being converted into a bluemira configuration store.
#
# These parameters mirror running the plasmod input demoH.i reference configuration

# %%

new_params = {
    "A": 3.1,
    "R_0": 9.002,
    "I_p": 17.75,
    "B_0": 5.855,
    "V_p": -2500,
    "v_burn": -1.0e6,
    "kappa_95": 1.652,
    "delta_95": 0.333,
    "delta": 0.38491934960310104,
    "kappa": 1.6969830041844367,
}

params = Configuration(new_params)

# Add parameter source
for param_name in params.keys():
    if param_name in new_params:
        param = params.get_param(param_name)
        param.source = "Plasmod Example"

# %%[markdown]
# Some values are not linked into bluemira. These plasmod parameters can be set
# directly in `problem_settings`.
# H-factor is set here as input therefore we will force plasmod to
# optimse to that H-factor.

# %%
problem_settings = {
    "pfus_req": 0.0,
    "pheat_max": 130.0,
    "q_control": 130.0,
    "Hfact": 1.1,
    "i_modeltype": "GYROBOHM_1",
    "i_equiltype": "Ip_sawtooth",
    "i_pedestal": "SAARELMA",
}

# %%[markdown]
# There are also some model choices that can be set in `problem_settings`.
# The available models with their options and explanations
# can be seen by running the below snippet.

# %%
for var_name in dir(plasmod.mapping):
    if "Model" in var_name and var_name != "Model":
        model = getattr(plasmod.mapping, var_name)
        model.info()

# %%[markdown]
# Finally the `build_config` dictionary collates the configuration settings for
# the solver

# %%
build_config = {
    "problem_settings": problem_settings,
    "mode": "run",
    "binary": binary,
}

# %%[markdown]
# Now we can create the solver object with the parameters and build configuration

# %%

plasmod_solver = plasmod.Solver(
    params=params,
    build_config=build_config,
)

# %%[markdown]
# These few functions are helpers to simplify the remainder of the tutorial.
# The first shows a few of the output scalar values and the second plots a
# given profile.

# %%


def print_outputs(plasmod_solver):
    """
    Print plasmod scalars
    """
    print(f"Fusion power [MW]: {plasmod_solver.params.P_fus/ 1E6}")
    print(
        f"Additional heating power [MW]: {plasmod_solver.get_raw_variables('Paux') / 1E6}"
    )
    print(f"Radiation power [MW]: {plasmod_solver.params.P_rad / 1E6}")
    print(f"Transport power across separatrix [MW]: {plasmod_solver.params.P_sep / 1E6}")
    print(f"{plasmod_solver.params.q_95}")
    print(f"{plasmod_solver.params.I_p}")
    print(f"{plasmod_solver.params.l_i}")
    print(f"{plasmod_solver.params.v_burn}")
    print(f"{plasmod_solver.params.Z_eff}")
    print(f"H-factor [-]: {plasmod_solver.get_raw_variables('Hfact')}")
    print(
        f"Divertor challenging criterion (P_sep * Bt /(q95 * R0 * A)) [-]: {plasmod_solver.get_raw_variables('psepb_q95AR')}"
    )
    print(
        f"H-mode operating regime f_LH = P_sep/P_LH [-]: {plasmod_solver.params.P_sep /plasmod_solver.params.P_LH}"
    )
    print(f"{plasmod_solver.params.tau_e}")
    print(f"Protium fraction [-]: {plasmod_solver.get_raw_variables('cprotium')}")
    print(f"Helium fraction [-]: {plasmod_solver.get_raw_variables('che')}")
    print(f"Xenon fraction [-]: {plasmod_solver.get_raw_variables('cxe')}")
    print(f"Argon fraction [-]: {plasmod_solver.get_raw_variables('car')}")


def plot_profile(plasmod_solver, var_name, var_unit):
    """
    Plot plasmod profile
    """
    prof = plasmod_solver.get_profile(var_name)
    x = plasmod_solver.get_profile("x")
    fig, ax = plt.subplots()
    ax.plot(x, prof)
    ax.set(xlabel="x (-)", ylabel=var_name + " (" + var_unit + ")")
    ax.grid()
    plt.show()


# %%[markdown]
# ### Running the solver
# Very simply use the `run` method of the solver

# %%

plasmod_solver.run()

# %%[markdown]
# ### Using the results
# Outputs can be accessed through 3 ways depending on the
# linking mechanism.
# 1. Through the `params` attribute which contains
#    all the bluemira linked parameters
# 2. Profiles can be accessed through the `get_profile` function
# 3. Unlinked plasmod parameters can be accessed through the
#    `get_raw_variables` function
#
# The list of available profiles can be seen by running the below cell.
# A good exercise would be to try showing a different profile in the plot.

# %%
print("Profiles")
pprint(list(plasmod.mapping.Profiles))

# %%
plot_profile(plasmod_solver, "Te", "keV")
print_outputs(plasmod_solver)

# %%[markdown]
# ### Rerunning with modified settings
# #### Changing the transport model

# %%
plasmod_solver.problem_settings["i_modeltype"] = "GYROBOHM_2"
plasmod_solver.run()
print_outputs(plasmod_solver)


# %%[markdown]
# #### Fixing fusion power to 2000 MW and safety factor `q_95` to 3.5.
# Plasmod calculates the additional heating power and the plasma current

# %%
plasmod_solver.params.q_95 = (3.5, "input")

plasmod_solver.problem_settings["pfus_req"] = 2000.0
plasmod_solver.problem_settings["i_equiltype"] = "q95_sawtooth"
plasmod_solver.problem_settings["q_control"] = 50.0

plasmod_solver.run()
print_outputs(plasmod_solver)

# %%[markdown]
# #### Setting heat flux on divertor target to 10 MW/m²
# plasmod calculates the argon concentration to fulfill the constraint

# %%
plasmod_solver.problem_settings["qdivt_sup"] = 10.0
plasmod_solver.run()
print_outputs(plasmod_solver)

# %%[markdown]
# #### Changing the mapping sending or recieving
# The mapping can be changed on a given parameter or set of parameters.
# Notice how the value of `q_95` doesn't change in the output
# even though its value has in the parameter (the previous value of 3.5 is used).

# %%
plasmod_solver.modify_mappings({"q_95": {"send": False}})
plasmod_solver.params.q_95 = (5, "input")
plasmod_solver.run()
print_outputs(plasmod_solver)
print("\nq_95 value history\n", plasmod_solver.params.q_95.history())
