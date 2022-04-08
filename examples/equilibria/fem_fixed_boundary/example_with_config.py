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
Configuration classes
"""


class Spherical(Configuration):
    """
    Spherical tokamak default configuration.
    """

    new_values = {
        "A": 1.67,
        "R_0": 2.5,
        "kappa_95": 2.857,
        "kappa": 3.2,
        "delta": 0.55,
        "delta_95": 0.367,
        "q_95": 4.509,
        "n_TF": 12,
    }

    def __init__(self, custom_params=new_values):
        super().__init__(custom_params)