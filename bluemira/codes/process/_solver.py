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

import copy
import os
from enum import auto
from typing import Dict, List, Tuple, Union

import numpy as np

from bluemira.base.look_and_feel import bluemira_warn
from bluemira.base.parameter import ParameterFrame
from bluemira.base.solver import RunMode as BaseRunMode
from bluemira.codes.error import CodesError
from bluemira.codes.interface import CodesSolver
from bluemira.codes.process._run import Run
from bluemira.codes.process._setup import Setup
from bluemira.codes.process._teardown import Teardown
from bluemira.codes.process.api import DEFAULT_INDAT, Impurities
from bluemira.codes.process.constants import BINARY as PROCESS_BINARY
from bluemira.codes.process.constants import NAME as PROCESS_NAME
from bluemira.codes.process.mapping import mappings as process_mappings
from bluemira.codes.utilities import add_mapping

BuildConfig = Dict[str, Union[float, str, "BuildConfig"]]


class RunMode(BaseRunMode):
    """
    Run modes for the PROCESS solver.
    """

    RUN = auto()
    RUNINPUT = auto()
    READ = auto()
    READALL = auto()
    MOCK = auto()
    NONE = auto()


class Solver(CodesSolver):
    """
    PROCESS solver. Runs, loads or mocks PROCESS to generate a reactor's
    radial build.

    Parameters
    ----------
    params: ParameterFrame
        ParameterFrame containing bluemira parameters for running, and
        extracting outputs from, PROCESS.
    build_config: Mapping[str, Mapping[float, str, BuildConfig]]
        Dictionary containing the configuration for this solver.
        Expected keys are:

        * binary: str
            The path to the PROCESS binary. The default assumes the
            PROCESS executable is on the system path.
        * run_dir: str
            The directory in which to run PROCESS. It is also the
            directory in which to look for PROCESS input and output
            files. Default is current working directory.
        * template_in_dat: str
            The path to a template IN.DAT file. The default is to use
            one provided by bluemira.
        * problem_settings: Mapping[str, float]
            Any PROCESS parameters that do not correspond to a bluemira
            parameter.

    Notes
    -----
    This solver has several run modes:

    * run: Run PROCESS to generate a radial build.
        Creates a new input file from the given template IN.DAT, which
        is modified with bluemira parameters that are mapped with
        :code:`send = True`.
    * runinput: Run PROCESS with an unmodified template IN.DAT.
        The template IN.DAT is not modified with bluemira parameters.
        This is equivalent to all bluemira parameters mappings having
        :code:`send = False`.
    * read: Load the radial build from a PROCESS MFILE.DAT.
        Loads only the parameters with :code:`send = True`.
        A file named 'MFILE.DAT' must exist within 'run_directory'.
    * readall: Load the radial build from a PROCESS MFILE.DAT.
        Loads all mappable parameters from the PROCESS file.
        A file named 'MFILE.DAT' must exist within 'run_directory'.
    * mock: Load bluemira parameters directly from a JSON file in the
        run directory. This does not run PROCESS.
    * none: Does nothing.
        PROCESS is not run and parameters are not updated. This is
        useful loading results form previous runs of bluemira, where
        overwriting data with PROCESS outputs would be undesirable.
    """

    name = PROCESS_NAME
    setup_cls = Setup
    run_cls = Run
    teardown_cls = Teardown
    run_mode_cls = RunMode

    def __init__(self, params: ParameterFrame, build_config: BuildConfig):
        # Init task objects on execution so parameters can be edited
        # between separate 'execute' calls.
        self._setup: Union[Setup, None] = None
        self._run: Union[Run, None] = None
        self._teardown: Union[Teardown, None] = None

        self.params = params
        add_mapping(PROCESS_NAME, self.params, process_mappings)

        _build_config = copy.deepcopy(build_config)
        self.binary = _build_config.pop("binary", PROCESS_BINARY)
        self.run_directory = _build_config.pop("run_dir", os.getcwd())
        self.read_directory = _build_config.pop("read_dir", os.getcwd())
        self.template_in_dat = _build_config.pop("template_in_dat", DEFAULT_INDAT)
        self.problem_settings = _build_config.pop("problem_settings", {})
        self.in_dat_path = _build_config.pop(
            "in_dat_path", os.path.join(self.run_directory, "IN.DAT")
        )
        if len(_build_config) > 0:
            quoted_delim = "', '"
            bluemira_warn(
                f"'{self.name}' solver received unknown build_config arguments: "
                f"'{quoted_delim.join(_build_config.keys())}'."
            )

    def execute(self, run_mode: RunMode) -> ParameterFrame:
        """
        Execute the solver in the given run mode.

        Parameters
        ----------
        run_mode: RunMode
            The run mode to execute the solver in. See the
            :func:`~bluemira.codes.process._solver.Solver.__init__`
            docstring for details of the behaviour of each run mode.
        """
        self._setup = Setup(
            self.params, self.in_dat_path, self.problem_settings, self.template_in_dat
        )
        self._run = Run(self.params, self.in_dat_path, self.binary)
        self._teardown = Teardown(self.params, self.run_directory, self.read_directory)

        if setup := self._get_execution_method(self._setup, run_mode):
            setup()
        if run := self._get_execution_method(self._run, run_mode):
            run()
        if teardown := self._get_execution_method(self._teardown, run_mode):
            teardown()

        return self.params

    def get_raw_variables(self, params: Union[List, str]):
        """
        Get raw variables from this solver's associate MFile.

        Mapped bluemira parameters will have bluemira names.

        Parameters
        ----------
        params: Union[List, str]
            Names of parameters to access.

        Returns
        -------
        values: List[float]
            The parameter values.
        """
        if self._teardown:
            return self._teardown.get_raw_outputs(params)
        raise CodesError(
            "Cannot retrieve output from PROCESS MFile. "
            "The solver has not been run, so no MFile is available to read."
        )

    @staticmethod
    def get_species_data(impurity: str) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Get species data from PROCESS section of OPEN-ADAS database.

        The data is taken with density $n_e = 10^{19} m^{-3}$.

        Parameters
        ----------
        impurity: str
            The impurity to get the species data for. This string should
            be one of the names in the
            :class:`~bluemira.codes.process.api.Impurities` Enum.

        Returns
        -------
        tref: np.ndarray
            The temperature in keV.
        l_ref: np.ndarray
            The loss function value $L_z(n_e, T_e)$ in W.m3.
        z_ref: np.ndarray
            Average effective charge.
        """
        t_ref, lz_ref, z_av_ref = np.genfromtxt(Impurities[impurity].file()).T
        return t_ref, lz_ref, z_av_ref

    def get_species_fraction(self, impurity: str) -> float:
        """
        Get species fraction for the given impurity.

        Parameters
        ----------
        impurity: str
            The impurity to get the species data for. This string should
            be one of the names in the
            :class:`~bluemira.codes.process.api.Impurities` Enum.

        Returns
        -------
        species_fraction: float
            The species fraction for the impurity taken from the PROCESS
            output MFile.
        """
        return self.get_raw_variables(Impurities[impurity].id())[0]
