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
"""Types for the optimisation module."""

from typing import Protocol, TypedDict

import numpy as np
from typing_extensions import NotRequired


class OptimiserCallable(Protocol):
    """Form for an optimiser function (objective, derivative, constraint, etc.)."""

    def __call__(self, x: np.ndarray) -> np.ndarray:
        """Call the optimiser function."""
        ...


class ConstraintT(TypedDict):
    """Typing for definition of a constraint."""

    f_constraint: OptimiserCallable
    tolerance: np.ndarray
    df_constraint: NotRequired[OptimiserCallable]
