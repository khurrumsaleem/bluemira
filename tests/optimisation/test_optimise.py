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
import numpy as np
import pytest

from bluemira.optimisation import Algorithm, optimise
from tests.optimisation.tools import d_rosenbrock, rosenbrock


class TestOptimise:
    @pytest.mark.parametrize(
        "algorithm", ["SLSQP", Algorithm.SBPLX, "MMA", Algorithm.BFGS]
    )
    def test_minimum_found_on_rosenbrock_no_bounds(self, algorithm):
        result = optimise(
            rosenbrock,
            algorithm=algorithm,
            df_objective=d_rosenbrock,
            dimensions=2,
            opt_conditions={"ftol_rel": 1e-6},
        )

        np.testing.assert_allclose(result.x, [1, 1])

    def test_history_recorded_given_keep_history_is_True(self):
        result = optimise(
            rosenbrock,
            algorithm="SLSQP",
            df_objective=d_rosenbrock,
            dimensions=2,
            opt_conditions={"ftol_rel": 1e-6},
            keep_history=True,
        )

        assert len(result.history) == result.n_evals
        # TODO(hsaunders1904):
        # do something to test that the history changes, i.e. we're not
        # just appending the same array every time

    @pytest.mark.parametrize(
        "algorithm",
        [
            Algorithm.SLSQP,
            "SBPLX",
            Algorithm.MMA,
            "BFGS",
            "DIRECT",
            Algorithm.DIRECT_L,
            "ISRES",
        ],
    )
    def test_grad_based_algs_find_min_on_rosenbrock_within_bounds(self, algorithm):
        result = optimise(
            rosenbrock,
            algorithm=algorithm,
            df_objective=d_rosenbrock,
            dimensions=2,
            opt_conditions={"ftol_rel": 1e-8, "max_eval": 5000},
            bounds=(np.array([0.5, 1.05]), np.array([0.95, 2])),
        )

        np.testing.assert_allclose(
            result.x,
            [0.95, 1.05],
            atol=0,
            rtol=1e-3,
            err_msg=f"after {result.n_evals} evals",
        )

    def test_ValueError_given_invalid_algorithm(self):
        with pytest.raises(ValueError):
            optimise(lambda: None, algorithm="NOT_AN_ALG")

    def test_ValueError_given_x0_and_dimensions_not_consistent(self):
        with pytest.raises(ValueError):
            optimise(
                rosenbrock,
                dimensions=3,
                x0=np.array([1, 1]),
                df_objective=d_rosenbrock,
                algorithm="SLSQP",
                opt_conditions={"ftol_rel": 1e-8, "max_eval": 5000},
                bounds=(np.array([0.5, 1.05]), np.array([0.95, 2])),
            )

    @pytest.mark.parametrize("alg", ["SLSQP", "COBYLA"])
    def test_nonlinear_constrain_optimisation(self, alg):
        """
        Test an optimisation with nonlinear constraints.

        See 'examples/nonlinearly_constrained_problem.py' for details of
        the problem.
        """

        def f_objective(x):
            return np.sqrt(x[1])

        def df_objective(x):
            return np.array([0.0, 0.5 / np.sqrt(x[1])])

        def f_constraint(x, a, b):
            return (a * x[0] + b) ** 3 - x[1]

        def df_constraint(x, a, b):
            return np.array([3 * a * (a * x[0] + b) * (a * x[0] + b), -1.0])

        result = optimise(
            f_objective,
            x0=np.array([1, 1]),
            algorithm=alg,
            df_objective=df_objective,
            opt_conditions={"xtol_rel": 1e-4, "max_eval": 3000},
            bounds=(np.array([-np.inf, 0]), np.array([np.inf, np.inf])),
            ineq_constraints=[
                {
                    "f_constraint": lambda x: f_constraint(x, 2, 0),
                    # Exclude df_constraint to test approx_derivative is doing work
                    "tolerance": np.array([1e-8]),
                },
                {
                    "f_constraint": lambda x: f_constraint(x, -1, 1),
                    "df_constraint": lambda x: df_constraint(x, -1, 1),
                    "tolerance": np.array([1e-8]),
                },
            ],
        )

        np.testing.assert_allclose(result.x, [1 / 3, 8 / 27], atol=1e-4)
