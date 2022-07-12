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
OptimisationProblems for coilset design.

New optimisation schemes for the coilset can be provided by subclassing
from CoilsetOP, which is an abstract base class for OptimisationProblems
that use a coilset as their parameterisation object.

Subclasses must provide an optimise() method that returns an optimised
coilset according to a given optimisation objective function.
As the exact form of the state vector that is optimised is often
specific to each objective function, each subclass of CoilsetOP is
generally also specific to a given objective function, since
the method used to map the coilset object to the state vector
(and additional required arguments) will generally differ in each case.

"""

import abc
from typing import List, Tuple

import numpy as np

import bluemira.equilibria.opt_objectives as objectives
from bluemira.equilibria.coils import CoilSet
from bluemira.equilibria.equilibrium import Breakdown, Equilibrium
from bluemira.equilibria.error import EquilibriaError
from bluemira.equilibria.opt_constraints import (
    FieldConstraints,
    MagneticConstraintSet,
    UpdateableConstraint,
)
from bluemira.equilibria.positioner import RegionMapper
from bluemira.utilities.opt_problems import (
    OptimisationConstraint,
    OptimisationObjective,
    OptimisationProblem,
)
from bluemira.utilities.opt_tools import regularised_lsq_fom, tikhonov
from bluemira.utilities.optimiser import Optimiser

__all__ = [
    "UnconstrainedTikhonovCurrentGradientCOP",
    "TikhonovCurrentCOP",
    "CoilsetPositionCOP",
    "NestedCoilsetPositionCOP",
]


class CoilsetOptimisationProblem(OptimisationProblem):
    """
    Abstract base class for OptimisationProblems for the coilset.
    Provides helper methods and utilities for OptimisationProblems
    using a coilset as their parameterisation object.

    Subclasses should provide an optimise() method that
    returns an optimised coilset object, optimised according
    to a specific objective function for that subclass.

    Parameters
    ----------
    coilset: Coilset
        Coilset to be optimised.
    optimiser: Optimiser (default: None)
        Optimiser object to use for constrained optimisation.
        Does not need to be provided if not used by
        optimise(), such as for purely unconstrained
        optimisation.
    objective: OptimisationObjective (default: None)
        OptimisationObjective storing objective information to
        provide to the Optimiser.
    constraints: List[OptimisationConstraint] (default: None)
        Optional list of OptimisationConstraint objects storing
        information about constraints that must be satisfied
        during the coilset optimisation, to be provided to the
        Optimiser.
    """

    def __init__(
        self,
        coilset: CoilSet,
        optimiser: Optimiser = None,
        objective: OptimisationObjective = None,
        constraints: List[OptimisationConstraint] = None,
    ):
        super().__init__(coilset, optimiser, objective, constraints)
        self.scale = 1e6  # current_scale
        self.initial_state, self.substates = self.read_coilset_state(
            self.coilset, self.scale
        )
        self.x0, self.z0, self.I0 = np.array_split(self.initial_state, self.substates)

    @property
    def coilset(self):
        return self._parameterisation

    @coilset.setter
    def coilset(self, value: CoilSet):
        self._parameterisation = value

    @staticmethod
    def read_coilset_state(coilset, current_scale):
        """
        Reads the input coilset and generates the state vector as an array to represent
        it.

        Parameters
        ----------
        coilset: Coilset
            Coilset to be read into the state vector.
        current_scale: float
            Factor to scale coilset currents down by for population of coilset_state.
            Used to minimise round-off errors in optimisation.

        Returns
        -------
        coilset_state: np.array
            State vector containing substate (position and current)
            information for each coil.
        substates: int
            Number of substates (blocks) in the state vector.
        """
        substates = 3
        x, z = coilset.get_positions()
        currents = coilset.get_control_currents() / current_scale

        coilset_state = np.concatenate((x, z, currents))
        return coilset_state, substates

    @staticmethod
    def set_coilset_state(coilset, coilset_state, current_scale):
        """
        Set the optimiser coilset from a provided state vector.

        Parameters
        ----------
        coilset: Coilset
            Coilset to set from state vector.
        coilset_state: np.array
            State vector representing degrees of freedom of the coilset,
            to be used to update the coilset.
        current_scale: float
            Factor to scale state vector currents up by when setting
            coilset currents.
            Used to minimise round-off errors in optimisation.
        """
        x, z, currents = np.array_split(coilset_state, 3)

        # coilset.set_positions not currently working for
        # SymmetricCircuits, it appears...
        # positions = list(zip(x, z))
        # self.coilset.set_positions(positions)
        for i, coil in enumerate(coilset.coils.values()):
            coil.x = x[i]
            coil.z = z[i]
        coilset.set_control_currents(currents * current_scale)

    @staticmethod
    def get_state_bounds(x_bounds, z_bounds, current_bounds):
        """
        Get bounds on the state vector from provided bounds on the substates.

        Parameters
        ----------
        x_bounds: tuple
            Tuple containing lower and upper bounds on the radial coil positions.
        z_bounds: tuple
            Tuple containing lower and upper bounds on the vertical coil positions.
        current_bounds: tuple
            Tuple containing bounds on the coil currents.

        Returns
        -------
        bounds: np.array
            Array containing state vectors representing lower and upper bounds
            for coilset state degrees of freedom.
        """
        lower_bounds = np.concatenate((x_bounds[0], z_bounds[0], current_bounds[0]))
        upper_bounds = np.concatenate((x_bounds[1], z_bounds[1], current_bounds[1]))
        bounds = np.array([lower_bounds, upper_bounds])
        return bounds

    @staticmethod
    def get_current_bounds(coilset, max_currents, current_scale):
        """
        Gets the scaled current vector bounds. Must be called prior to optimise.

        Parameters
        ----------
        coilset: Coilset
            Coilset to fetch current bounds for.
        max_currents: float or np.ndarray
            Maximum magnitude of currents in each coil [A] permitted during optimisation.
            If max_current is supplied as a float, the float will be set as the
            maximum allowed current magnitude for all coils.
            If the coils have current density limits that are more restrictive than these
            coil currents, the smaller current limit of the two will be used for each
            coil.
        current_scale: float
            Factor to scale coilset currents down when returning scaled current limits.

        Returns
        -------
        current_bounds: (np.narray, np.narray)
            Tuple of arrays containing lower and upper bounds for currents
            permitted in each control coil.
        """
        n_control_currents = len(coilset.get_control_currents())
        scaled_input_current_limits = np.inf * np.ones(n_control_currents)

        if max_currents is not None:
            input_current_limits = np.asarray(max_currents)
            input_size = np.size(np.asarray(input_current_limits))
            if input_size == 1 or input_size == n_control_currents:
                scaled_input_current_limits = input_current_limits / current_scale
            else:
                raise EquilibriaError(
                    "Length of max_currents array provided to optimiser is not"
                    "equal to the number of control currents present."
                )

        # Get the current limits from coil current densities
        # TODO: Ensure consistent scaling when fetching from coilset
        coilset_current_limits = coilset.get_max_currents(0.0)
        if len(coilset_current_limits) != n_control_currents:
            raise EquilibriaError(
                "Length of array containing coilset current limits"
                "is not equal to the number of control currents in optimiser."
            )

        # Limit the control current magnitude by the smaller of the two limits
        control_current_limits = np.minimum(
            scaled_input_current_limits, coilset_current_limits
        )
        current_bounds = (-control_current_limits, control_current_limits)

        return current_bounds

    def update_magnetic_constraints(self, I_not_dI=True, fixed_coils=True):
        """
        Update the magnetic optimisation constraints with the state of the Equilibrium
        """
        if self._constraints is not None:
            for constraint in self._constraints:
                if isinstance(constraint, UpdateableConstraint):
                    constraint.prepare(
                        self.eq, I_not_dI=I_not_dI, fixed_coils=fixed_coils
                    )
                if "scale" in constraint._args:
                    constraint._args["scale"] = self.scale


class CoilsetPositionCOP(CoilsetOptimisationProblem):
    """
    Coilset OptimisationProblem for coil currents and positions
    subject to maximum current bounds and positions bounded within
    a provided region.

    Coil currents and positions are optimised simultaneously.

    Parameters
    ----------
    coilset: CoilSet
        Coilset to optimise.
    eq: Equilibrium
        Equilibrium object used to update magnetic field targets.
    targets: MagneticConstraintSet
        Set of magnetic field targets to use in objective function.
    pfregions: dict(coil_name:Loop, coil_name:Loop, ...)
        Dictionary of loops that specify convex hull regions inside which
        each PF control coil position is to be optimised.
        The loop objects must be 2d in x,z in units of [m].
    max_currents: float or np.array(len(coilset._ccoils)) (default = None)
        Maximum allowed current for each independent coil current in coilset [A].
        If specified as a float, the float will set the maximum allowed current
        for all coils.
    gamma: float (default = 1e-8)
        Tikhonov regularisation parameter in units of [A⁻¹].
    optimiser: Optimiser
        Optimiser object to use for constrained optimisation.
    constraints: List[OptimisationConstraint] (default: None)
        Optional list of OptimisationConstraint objects storing
        information about constraints that must be satisfied
        during the coilset optimisation, to be provided to the
        optimiser.

    Notes
    -----
    Setting stopval and maxeval is the most reliable way to stop optimisation
    at the desired figure of merit and number of iterations respectively.
    Some NLOpt optimisers display unexpected behaviour when setting xtol and
    ftol, and may not terminate as expected when those criteria are reached.
    """

    def __init__(
        self,
        coilset: CoilSet,
        eq: Equilibrium,
        targets: MagneticConstraintSet,
        pfregions: dict,
        max_currents=None,
        gamma=1e-8,
        optimiser=Optimiser(
            algorithm_name="SBPLX",
            opt_conditions={
                "stop_val": 1.0,
                "max_eval": 100,
            },
        ),
        constraints=None,
    ):
        # noqa :N803

        # Create region map
        self.region_mapper = RegionMapper(pfregions)

        # Store inputs (optional, but useful for constraints)
        self.eq = eq
        self.targets = targets

        # Set objective function for this OptimisationProblem,
        # and initialise
        objective = OptimisationObjective(
            objectives.ad_objective,
            {"objective": self.get_state_figure_of_merit, "objective_args": {}},
        )
        super().__init__(coilset, optimiser, objective, constraints)

        # Set up bounds
        bounds = self.get_mapped_state_bounds(self.region_mapper, max_currents)
        # Add bounds information to help automatic differentiation of objective
        self._objective._args["ad_args"] = {"bounds": bounds}
        self._objective._args["objective_args"] = {
            "coilset": coilset,
            "eq": eq,
            "targets": targets,
            "region_mapper": self.region_mapper,
            "current_scale": self.scale,
            "gamma": gamma,
        }

        # Set up optimiser
        dimension = len(bounds[0])
        self.set_up_optimiser(dimension, bounds)

    def get_mapped_state_bounds(self, region_mapper: RegionMapper, max_currents):
        """
        Get mapped bounds on the coilset state vector from the coil regions and
        maximum coil currents.

        Parameters
        ----------
        region_mapper: RegionMapper
            RegionMapper mapping coil positions within the allowed optimisation
            regions.
        max_currents float or np.array(len(coilset._ccoils)) (default = None)
            Maximum allowed current for each independent coil current in coilset [A].
            If specified as a float, the float will set the maximum allowed current
            for all coils.

        Returns
        -------
        bounds: np.array
            Array containing state vectors representing lower and upper bounds
            for coilset state degrees of freedom.
        """
        # Get mapped position bounds from RegionMapper
        _, lower_lmap_bounds, upper_lmap_bounds = region_mapper.get_Lmap(self.coilset)
        current_bounds = self.get_current_bounds(self.coilset, max_currents, self.scale)

        lower_bounds = np.concatenate((lower_lmap_bounds, current_bounds[0]))
        upper_bounds = np.concatenate((upper_lmap_bounds, current_bounds[1]))
        bounds = (lower_bounds, upper_bounds)
        return bounds

    def optimise(self):
        """
        Optimiser handle. Used in __call__

        Returns
        -------
        self.coilset: CoilSet
            Optimised CoilSet object.
        """
        # Get initial state and apply region mapping to coil positions.
        initial_state, _ = self.read_coilset_state(self.coilset, self.scale)
        _, _, initial_currents = np.array_split(initial_state, self.substates)
        initial_mapped_positions, _, _ = self.region_mapper.get_Lmap(self.coilset)
        initial_mapped_state = np.concatenate(
            (initial_mapped_positions, initial_currents)
        )

        # Optimise
        state = self.opt.optimise(initial_mapped_state)

        # Call objective function final time on optimised state
        # to set coilset.
        # Necessary as optimised state may not always be the final
        # one evaluated by optimiser.
        self._objective(state, np.empty(shape=(0, 0)))
        return self.coilset

    @staticmethod
    def get_state_figure_of_merit(
        vector,
        grad,
        coilset: CoilSet,
        eq: Equilibrium,
        targets: MagneticConstraintSet,
        region_mapper: RegionMapper,
        current_scale: float,
        gamma: float,
    ):
        """
        Calculates figure of merit from objective function,
        consisting of a least-squares objective with Tikhonov
        regularisation term, which updates the gradient in-place.

        Parameters
        ----------
        vector: np.array
            State vector. Numpy array formed by concatenation of coil radial
            coordinates, coil vertical coordinates, and (scaled) coil currents.
        grad: np.array
            Dummy variable for NLOpt calls. Not updated.
        coilset: CoilSet
            CoilSet to update using state vector.
        eq: Equilibrium
            Equilibrium object used to update magnetic field targets.
        targets: MagneticConstraintSet
            Set of magnetic field targets to optimise Equilibrium towards,
            using least-squares objective with Tikhonov regularisation.
        region_mapper: RegionMapper
            RegionMapper mapping coil positions within the allowed optimisation
            regions.
        current_scale: float
            Scale factor to scale currents in state vector up by to
            give currents in [A].
        gamma: float
            Tikhonov regularisation parameter in units of [A⁻¹].

        Returns
        -------
        fom: float
            Value of objective function (figure of merit).
        """
        mapped_x, mapped_z, currents = np.array_split(vector, 3)
        mapped_positions = np.concatenate((mapped_x, mapped_z))
        region_mapper.set_Lmap(mapped_positions)
        x_vals, z_vals = region_mapper.get_xz_arrays()
        coilset_state = np.concatenate((x_vals, z_vals, currents))

        CoilsetOptimisationProblem.set_coilset_state(
            coilset, coilset_state, current_scale
        )

        # Update target
        eq._remap_greens()

        # Set up data needed in FoM evaluation.
        # Scale the control matrix and constraint vector by weights.
        targets(eq, I_not_dI=True, fixed_coils=False)
        _, a_mat, b_vec = targets.get_weighted_arrays()

        # Calculate objective function
        fom, err = regularised_lsq_fom(currents * current_scale, a_mat, b_vec, gamma)
        return fom


class NestedCoilsetPositionCOP(CoilsetOptimisationProblem):
    """
    Coilset OptimisationProblem for coil currents and positions
    subject to maximum current bounds and positions bounded within
    a provided region. Performs a nested optimisation for coil
    currents within each position optimisation function call.

    Parameters
    ----------
    sub_opt: CoilsetOP
        Coilset OptimisationProblem to use for the optimisation of
        coil currents at each trial set of coil positions.
        sub_opt.coilset must exist, and will be modified
        during the optimisation.
    eq: Equilibrium
        Equilibrium object used to update magnetic field targets.
    targets: MagneticConstraintSet
        Set of magnetic field targets to use in objective function.
    pfregions: dict(coil_name:Loop, coil_name:Loop, ...)
        Dictionary of loops that specify convex hull regions inside which
        each PF control coil position is to be optimised.
        The loop objects must be 2d in x,z in units of [m].
    optimiser: Optimiser
        Optimiser object to use for constrained optimisation.
    constraints: List[OptimisationConstraint] (default: None)
        Optional list of OptimisationConstraint objects storing
        information about constraints that must be satisfied
        during the coilset optimisation, to be provided to the
        optimiser.

    Notes
    -----
    Setting stopval and maxeval is the most reliable way to stop optimisation
    at the desired figure of merit and number of iterations respectively.
    Some NLOpt optimisers display unexpected behaviour when setting xtol and
    ftol, and may not terminate as expected when those criteria are reached.
    """

    def __init__(
        self,
        sub_opt: CoilsetOptimisationProblem,
        eq: Equilibrium,
        targets: MagneticConstraintSet,
        pfregions: dict,
        optimiser=Optimiser(
            algorithm_name="SBPLX",
            opt_conditions={
                "stop_val": 1.0,
                "max_eval": 100,
            },
        ),
        constraints: List[OptimisationConstraint] = None,
    ):
        # noqa :N803

        # Create region map
        self.region_mapper = RegionMapper(pfregions)

        # Store inputs (optional, but useful for constraints)
        self.eq = eq
        self.targets = targets

        # Set objective function for this OptimisationProblem,
        # and initialise
        objective = OptimisationObjective(
            objectives.ad_objective,
            {"objective": self.get_state_figure_of_merit, "objective_args": {}},
        )
        super().__init__(sub_opt.coilset, optimiser, objective, constraints)

        # Set up bounds
        _, lower_bounds, upper_bounds = self.region_mapper.get_Lmap(self.coilset)
        bounds = (lower_bounds, upper_bounds)
        # Add bounds information to help automatic differentiation of objective
        self._objective._args["ad_args"] = {"bounds": bounds}
        self._objective._args["objective_args"] = {
            "coilset": self.coilset,
            "eq": eq,
            "targets": targets,
            "region_mapper": self.region_mapper,
            "current_scale": self.scale,
            "initial_currents": self.I0,
            "sub_opt": sub_opt,
        }
        # Set up optimiser
        dimension = len(bounds[0])
        self.set_up_optimiser(dimension, bounds)

    def optimise(self):
        """
        Optimiser handle. Used in __call__

        Returns
        -------
        self.coilset: CoilSet
            Optimised CoilSet object.
        """
        # Get initial currents, and trim to within current bounds.
        initial_state, substates = self.read_coilset_state(self.coilset, self.scale)
        _, _, initial_currents = np.array_split(initial_state, substates)
        intial_mapped_positions, _, _ = self.region_mapper.get_Lmap(self.coilset)

        # Optimise
        self._objective._args["objective_args"]["initial_currents"] = initial_currents
        positions = self.opt.optimise(intial_mapped_positions)

        # Call objective function final time on optimised state
        # to set coilset.
        # Necessary as optimised state may not always be the final
        # one evaluated by optimiser.
        self._objective(positions, np.empty(shape=(0, 0)))
        return self.coilset

    @staticmethod
    def get_state_figure_of_merit(
        vector,
        grad,
        coilset: CoilSet,
        eq: Equilibrium,
        targets: MagneticConstraintSet,
        region_mapper: RegionMapper,
        current_scale: float,
        initial_currents,
        sub_opt: CoilsetOptimisationProblem,
    ):
        """
        Calculates figure of merit, returned from the current
        optimiser at each trial coil position.

        Parameters
        ----------
        vector: np.array(n_C)
            State vector of the array of coil positions.
        grad: np.array
            Dummy variable for NLOpt calls. Not updated.
        coilset: CoilSet
            CoilSet to update using state vector.
        eq: Equilibrium
            Equilibrium object used to update magnetic field targets.
        targets: MagneticConstraintSet
            Set of magnetic field targets to update for use in sub_opt.
        region_mapper: RegionMapper
            RegionMapper mapping coil positions within the allowed optimisation
            regions.
        current_scale: float
            Scale factor to scale currents in state vector up by to
            give currents in [A].
        initial_currents: np.array
            Array containing initial (scaled) coil currents prior to passing
            to sub_opt
        sub_opt: CoilsetOP
            Coilset OptimisationProblem used to optimise the array of coil
            currents at each trial position.

        Returns
        -------
        fom: float
            Value of objective function (figure of merit).
        """
        region_mapper.set_Lmap(vector)
        x_vals, z_vals = region_mapper.get_xz_arrays()
        positions = np.concatenate((x_vals, z_vals))
        coilset_state = np.concatenate((positions, initial_currents))
        CoilsetOptimisationProblem.set_coilset_state(
            coilset, coilset_state, current_scale
        )

        # Update targets
        eq._remap_greens()
        targets(eq, I_not_dI=True, fixed_coils=False)

        # Calculate objective function
        sub_opt()
        fom = sub_opt.opt.optimum_value
        return fom


class UnconstrainedTikhonovCurrentGradientCOP(CoilsetOptimisationProblem):
    """
    Unbounded, unconstrained, analytically optimised current gradient vector for minimal
    error to the L2-norm of a set of magnetic constraints (used here as targets).

    This is useful for getting a preliminary Equilibrium

    Parameters
    ----------
    coilset: CoilSet
        CoilSet object to optimise with
    eq: Equilibrium
        Equilibrium object to optimise for
    targets: MagneticConstraintSet
        Set of magnetic constraints to minimise the error for
    gamma: float
        Tikhonov regularisation parameter [1/A]
    """

    def __init__(self, coilset, eq, targets, gamma):
        self.eq = eq
        self.targets = targets
        self.gamma = gamma

        super().__init__(coilset)

    def optimise(self, *args, **kwargs):
        """
        Optimise the prescribed problem.

        Notes
        -----
        The weight vector is used to scale the response matrix and
        constraint vector. The weights are assumed to be uncorrelated, such that the
        weight matrix W_ij used to define (for example) the least-squares objective
        function (Ax - b)ᵀ W (Ax - b), is diagonal, such that
        weights[i] = w[i] = sqrt(W[i,i]).
        """
        # Scale the control matrix and magnetic field targets vector by weights.
        self.targets(self.eq, I_not_dI=False)
        _, a_mat, b_vec = self.targets.get_weighted_arrays()

        # Optimise currents using analytic expression for optimum.
        current_adjustment = tikhonov(a_mat, b_vec, self.gamma)

        # Update parameterisation (coilset).
        self.coilset.adjust_currents(current_adjustment)
        return self.coilset


class TikhonovCurrentCOP(CoilsetOptimisationProblem):
    """
    Coilset OptimisationProblem for coil currents subject to maximum current bounds.

    Coilset currents optimised using objectives.regularised_lsq_objective as
    objective function.

    Parameters
    ----------
    coilset: CoilSet
        Coilset to optimise.
    eq: Equilibrium
        Equilibrium object used to update magnetic field targets.
    targets: MagneticConstraintSet
        Set of magnetic field targets to use in objective function.
    gamma: float (default = 1e-8)
        Tikhonov regularisation parameter in units of [A⁻¹].
    max_currents float or np.array(len(coilset._ccoils)) (default = None)
        Maximum allowed current for each independent coil current in coilset [A].
        If specified as a float, the float will set the maximum allowed current
        for all coils.
    optimiser: Optimiser
        Optimiser object to use for constrained optimisation.
    constraints: List[OptimisationConstraint] (default: None)
        Optional list of OptimisationConstraint objects storing
        information about constraints that must be satisfied
        during the coilset optimisation, to be provided to the
        optimiser.
    """

    def __init__(
        self,
        coilset,
        eq,
        targets,
        gamma,
        optimiser: Optimiser = Optimiser(
            algorithm_name="SLSQP",
            opt_conditions={
                "xtol_rel": 1e-4,
                "xtol_abs": 1e-4,
                "ftol_rel": 1e-4,
                "ftol_abs": 1e-4,
                "max_eval": 100,
            },
            opt_parameters={"initial_step": 0.03},
        ),
        max_currents=None,
        constraints=None,
    ):
        self.eq = eq
        self.targets = targets
        objective = OptimisationObjective(
            objectives.regularised_lsq_objective, f_objective_args={"gamma": gamma}
        )

        super().__init__(coilset, optimiser, objective, constraints=constraints)

        bounds = self.get_current_bounds(self.coilset, max_currents, self.scale)
        dimension = len(bounds[0])
        self.set_up_optimiser(dimension, bounds)

    def optimise(self, fixed_coils=True):
        """
        Solve the optimisation problem

        Parameters
        ----------
        fixed_coils: True
            Whether or not to update to coilset response matrices

        Returns
        -------
        coilset: CoilSet
            Optimised CoilSet
        """
        # Scale the control matrix and magnetic field targets vector by weights.
        self.targets(self.eq, I_not_dI=True, fixed_coils=fixed_coils)
        _, a_mat, b_vec = self.targets.get_weighted_arrays()

        self._objective._args["scale"] = self.scale
        self._objective._args["a_mat"] = a_mat
        self._objective._args["b_vec"] = b_vec

        self.update_magnetic_constraints(I_not_dI=True, fixed_coils=fixed_coils)

        initial_state, n_states = self.read_coilset_state(self.coilset, self.scale)
        _, _, initial_currents = np.array_split(initial_state, n_states)

        initial_currents = np.clip(
            initial_currents, self.opt.lower_bounds, self.opt.upper_bounds
        )
        currents = self.opt.optimise(initial_currents)
        self.coilset.set_control_currents(currents * self.scale)
        return self.coilset


class MinimalCurrentCOP(CoilsetOptimisationProblem):
    """
    Bounded, constrained, minimal current optimisation problem.

    Parameters
    ----------
    eq: Equilibrium
        Equilibrium object to optimise the currents for
    optimiser: Optimiser
        Optimiser object to use
    max_currents: np.ndarray
        Current bounds vector [A]
    constraints: Optional[List[OptimisationConstraint]]
        List of optimisation constraints to apply to the optimisation problem
    """

    def __init__(self, coilset, eq, optimiser, max_currents=None, constraints=None):
        self.eq = eq
        objective = OptimisationObjective(
            objectives.minimise_coil_currents, f_objective_args={}
        )
        super().__init__(coilset, optimiser, objective, constraints)

        bounds = self.get_current_bounds(self.coilset, max_currents, self.scale)
        dimension = len(bounds[0])
        self.set_up_optimiser(dimension, bounds)

    def optimise(self, fixed_coils=True):
        """
        Solve the optimisation problem

        Parameters
        ----------
        fixed_coils: True
            Whether or not to update to coilset response matrices

        Returns
        -------
        coilset: CoilSet
            Optimised CoilSet
        """
        self.update_magnetic_constraints(I_not_dI=True, fixed_coils=fixed_coils)

        initial_state, n_states = self.read_coilset_state(self.eq.coilset, self.scale)
        _, _, initial_currents = np.array_split(initial_state, n_states)

        initial_currents = np.clip(
            initial_currents, self.opt.lower_bounds, self.opt.upper_bounds
        )
        currents = self.opt.optimise(initial_currents)
        self.coilset.set_control_currents(currents * self.scale)
        return self.coilset


class BreakdownZoneStrategy(abc.ABC):
    """
    Abstract base class for the definition of a breakdown zone strategy.

    Parameters
    ----------
    R_0: float
        Major radius of the reference plasma
    A: float
        Aspect ratio of the reference plasma
    tk_sol: float
        Thickness of the scrape-off layer
    """

    def __init__(self, R_0, A, tk_sol, **kwargs):
        self.R_0 = R_0
        self.A = A
        self.tk_sol = tk_sol

    @abc.abstractproperty
    def breakdown_point(self) -> Tuple[float]:
        """
        The location of the breakdown point.

        Returns
        -------
        x_c: float
            Radial coordinate of the breakdown point
        z_c: float
            Vertical coordinate of the breakdown point
        """
        pass

    @abc.abstractproperty
    def breakdown_radius(self) -> float:
        """
        The radius of the breakdown zone.
        """
        pass

    @abc.abstractmethod
    def calculate_zone_points(self, n_points: int) -> Tuple[np.ndarray]:
        """
        Calculate the discretised set of points representing the breakdown zone.
        """
        pass


class CircularZoneStrategy(BreakdownZoneStrategy):
    """
    Circular breakdown zone strategy.
    """

    def calculate_zone_points(self, n_points: int) -> Tuple[np.ndarray]:
        """
        Calculate the discretised set of points representing the breakdown zone.
        """
        x_c, z_c = self.breakdown_point
        r_c = self.breakdown_radius
        theta = np.linspace(0, 2 * np.pi, n_points - 1, endpoint=False)
        x = x_c + r_c * np.cos(theta)
        z = z_c + r_c * np.sin(theta)
        x = np.append(x, x_c)
        z = np.append(z, z_c)
        return x, z


class InboardBreakdownZoneStrategy(CircularZoneStrategy):
    """
    Inboard breakdown zone strategy.
    """

    @property
    def breakdown_point(self) -> Tuple[float]:
        r_c = self.breakdown_radius
        x_c = self.R_0 - self.R_0 / self.A - self.tk_sol + r_c
        z_c = 0.0
        return x_c, z_c

    @property
    def breakdown_radius(self) -> float:
        return 0.5 * self.R_0 / self.A


class OutboardBreakdownZoneStrategy(CircularZoneStrategy):
    """
    Outboard breakdown zone strategy.
    """

    @property
    def breakdown_point(self) -> Tuple[float]:
        r_c = self.breakdown_radius
        x_c = self.R_0 + self.R_0 / self.A + self.tk_sol - r_c
        z_c = 0.0
        return x_c, z_c

    @property
    def breakdown_radius(self) -> float:
        return 0.7 * self.R_0 / self.A


class InputBreakdownZoneStrategy(CircularZoneStrategy):
    """
    User input breakdown zone strategy.
    """

    def __call__(self, *args, **kwargs):
        return self

    def __init__(self, x_c, z_c, r_c):
        self.x_c = x_c
        self.z_c = z_c
        self.r_c = r_c

    @property
    def breakdown_point(self) -> Tuple[float]:
        return self.x_c, self.z_c

    @property
    def breakdown_radius(self) -> float:
        return self.r_c


class BreakdownCOP(CoilsetOptimisationProblem):
    """
    Coilset optimisation problem for the premagnetisation / breakdown phase.
    """

    def __init__(
        self,
        coilset: CoilSet,
        breakdown: Breakdown,
        breakdown_strategy: BreakdownZoneStrategy,
        B_stray_max,
        B_stray_con_tol,
        n_B_stray_points,
        optimiser: Optimiser = None,
        max_currents=None,
        constraints: List[OptimisationConstraint] = None,
    ):
        self.eq = breakdown
        self.scale = 1e6  # current_scale

        objective = OptimisationObjective(
            objectives.maximise_flux,
            f_objective_args={
                "c_psi_mat": np.array(
                    coilset.control_psi(*breakdown_strategy.breakdown_point)
                ),
                "scale": self.scale,
            },
        )

        x_zone, z_zone = breakdown_strategy.calculate_zone_points(n_B_stray_points)

        stray_field_cons = FieldConstraints(
            x_zone, z_zone, B_max=B_stray_max, tolerance=B_stray_con_tol
        )

        if constraints:
            constraints.append(stray_field_cons)
        else:
            constraints = [stray_field_cons]

        super().__init__(coilset, optimiser, objective, constraints)

        # Set up optimiser
        bounds = (-max_currents / self.scale, max_currents / self.scale)
        dimension = len(bounds[0])
        self.set_up_optimiser(dimension, bounds)

    def optimise(self, x0=None, fixed_coils=True):
        """
        Solve the optimisation problem.
        """
        if x0 is None:
            x0 = 1e-6 * np.ones(self.coilset.n_control)
        else:
            x0 = np.array(x0) / self.scale

        self.update_magnetic_constraints(I_not_dI=True, fixed_coils=fixed_coils)

        initial_state, n_states = self.read_coilset_state(self.coilset, self.scale)
        _, _, initial_currents = np.array_split(initial_state, n_states)

        initial_currents = np.clip(
            initial_currents, self.opt.lower_bounds, self.opt.upper_bounds
        )
        currents = self.opt.optimise(initial_currents)
        self.coilset.set_control_currents(currents * self.scale)
        return self.coilset
