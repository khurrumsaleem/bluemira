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
Full fuel cycle model object
"""
import matplotlib.pyplot as plt
import numpy as np
from scipy.interpolate import interp1d

from bluemira.base.constants import N_AVOGADRO, T_LAMBDA, T_MOLAR_MASS, YR_TO_S, raw_uc
from bluemira.base.look_and_feel import bluemira_print
from bluemira.base.parameter import ParameterFrame
from bluemira.fuel_cycle.blocks import FuelCycleComponent, FuelCycleFlow
from bluemira.fuel_cycle.tools import (
    _speed_recycle,
    discretise_1d,
    find_max_load_factor,
    find_noisy_locals,
    legal_limit,
)

# TODO: Make the whole thing run in self.t (higher resolution, better plotting)
# It will be slower... and it will probably be less accurate! But the plots..
# FIXED: You hacked the plot


class EUDEMOFuelCycleModel:
    """
    Tritium fuel cycle object.

    Takes a lifecycle timeline and interprets it to reach tritium start-up
    inventory and inventory doubling time estimates.

    Parameters
    ----------
    timeline: Timeline object
        The timeline with which to run the FuelCycle

    Other Parameters
    ----------------
    A: float
        [1=100%] DEMO load factor - read from lifecycle output
    f_b: float
        [1=100%] Tritium burnup fraction in plasma
    TBR: float
        [T/T_{fused}] Reactor engineering tritium breeding fraction
    eta_f: float
        [1=100%] Fuelling efficiency
    t_c_TFV: float
        Tritium exhaust cycle time [s]
    t_c_BB: float
        Blanket tritium exhaust cycle time [s]
    I_ivc: float
        In-vessel environment maximum absorbed T inventory [s]
    I_tfv: float
        Tritium fuel cycle systems maximum absorbed T inventory [kg]
    I_bb: float
        Blanket maximum absorbed T inventory [kg]
    eta_ivc: float
        [1=100%] T exhaust efficiency of in-vessel environment
    eta_tfv: float
        [1=100%] T exhaust efficiency of in-vessel environment
    eta_bb: float
        [1=100%] T exhaust efficiency of blanket
    """

    # fmt: off
    default_params = [
        ['TBR', 'Tritium breeding ratio', 1.05, 'dimensionless', None, 'Default'],
        ['f_b', 'Burn-up fraction', 0.015, 'dimensionless', None, 'Default'],
        ['m_gas', 'Gas puff flow rate', 50, 'Pa m^3/s', 'To maintain detachment - no chance of fusion from gas injection', 'Discussions with Chris Day and Yannick Hörstenmeyer'],
        ['A_global', 'Load factor', 0.3, 'dimensionless', None, 'Default'],
        ['r_learn', 'Learning rate', 1, 'dimensionless', None, 'Default'],
        ['t_pump', 'Time in DIR loop', 100, 's', 'Time between exit from plasma and entry into plasma through DIR loop', 'Discussions with Chris Day and Yannick Hörstenmeyer'],
        ['t_exh', 'Time in INDIR loop', 3600, 's', 'Time between exit from plasma and entry into TFV systems INDIR', 'Default'],
        ['t_ters', 'Time from BB exit to TFV system', 5 * 3600, 's', None, 'Default'],
        ['t_freeze', 'Time taken to freeze pellets', 1800, 's', None, 'Discussions with Chris Day and Yannick Hörstenmeyer'],
        ['f_dir', 'Fraction of flow through DIR loop', 0.9, 'dimensionless', None, 'Discussions with Chris Day and Yannick Hörstenmeyer'],
        ['t_detrit', 'Time in detritiation system', 10 * 3600, 's', None, 'Default'],
        ['f_detrit_split', 'Fraction of detritiation line tritium extracted', 0.9999, 'dimensionless', None, 'Default'],
        ['f_exh_split', 'Fraction of exhaust tritium extracted', 0.99, 'dimensionless', None, 'Default'],
        ['eta_fuel_pump', 'Efficiency of fuel line pump', 0.9, 'dimensionless', 'Pump which pumps down the fuelling lines', 'Default'],
        ['eta_f', 'Fuelling efficiency', 0.5, 'dimensionless', 'Efficiency of the fuelling lines prior to entry into the VV chamber', 'Default'],
        ['I_miv', 'Maximum in-vessel T inventory', 0.3, 'kg', None, 'Default'],
        ['I_tfv_min', 'Minimum TFV inventory', 2, 'kg', 'Without which e.g. cryodistillation columns are not effective', "Discussions with Chris Day and Jonas Schwenzer (N.B. working assumptions only)"],
        ['I_tfv_max', 'Maximum TFV inventory', 2.2, 'kg', "Account for T sequestration inside the T plant", "Discussions with Chris Day and Jonas Schwenzer (N.B. working assumptions only)"],
        ['I_mbb', 'Maximum BB T inventory', 0.055, 'kg', None, 'Default'],
        ['eta_iv', 'In-vessel bathtub parameter', 0.9995, 'dimensionless', None, 'Default'],
        ['eta_bb', 'BB bathtub parameter', 0.995, 'dimensionless', None, 'Default'],
        ['eta_tfv', 'TFV bathtub parameter', 0.998, 'dimensionless', None, 'Default'],
        ['f_terscwps', 'TERS and CWPS cumulated factor', 0.9999, 'dimensionless', None, 'Default']
    ]
    # fmt: on

    def __init__(self, config, inputs):
        # Handle parameters
        self.params = ParameterFrame(self.default_params)
        self.params.update_kw_parameters(
            config, source=f"{self.__class__.__name__} input"
        )

        # Handle calculation information
        self.verbose = inputs.get("verbose", False)
        self.timestep = inputs.get("timestep", 1200)
        self.conv_thresh = inputs.get("conv_thresh", 0.0002)
        self.n = inputs.get("n", None)

    def _constructors(self):
        # Constructors (untangling the spaghetti)
        self.max_T = None
        self.min_T = None
        self.m_T = None
        self.m_dot_release = None
        self.m_T_in = None
        self.m_T_req = None
        self.m_T_start = None
        self.M_T_bred = None
        self.M_T_stack = None
        self.M_T_burnt = None
        self.I_blanket = None
        self.I_plasma = None
        self.I_stack = None
        self.I_tfv = None

        self.grate = None
        self.brate = None
        self.prate = None
        self.DEMO_rt = None
        self.DEMO_t = None
        self.DD_rate = None
        self.DT_rate = None
        self.bci = None
        self.arg_t_d = None
        self.arg_t_infl = None
        self.t = None
        self.t_d = None
        self.t_infl = None

    def run(self, timeline):
        """
        Run the fuel cycle model.

        Parameters
        ----------
        timeline: Timeline
            Timeline with which to run the model
        """
        if self.n is None:
            self.n = len(timeline["time"])

        self.A_global = timeline["A_global"]

        self._constructors()
        self.initialise_arrays(timeline, self.n)
        # Initialise model with a reasonable number for decay
        self.seed_t()
        self.iterations = 0
        self.recycle()
        self.finalise()
        self.m_T_req += self.I_tfv[0]  # Add TFV fountain inventory
        self.m_dot_release = self.calc_m_release()

    def finalise(self):
        """
        Perform clean-up fudge to ensure all tritium returns to stores after
        the end of the reactor life.
        """
        n_bins = max(int(len(self.m_T) / 4500), 400)
        # Hand tweak to get findnoisylocals looking good
        self.max_T = find_noisy_locals(self.m_T, x_bins=n_bins, mode="max")
        self.min_T = find_noisy_locals(self.m_T, x_bins=n_bins)
        # self.max_T[1][-1] = self.max_T[1][-2]   #plothack
        self.m_T[-1] = self.max_T[1][-1]
        self.arg_t_d, self.t_d = self.calc_t_d()
        self.arg_t_infl, self.t_infl = self.calc_t_infl()

    def initialise_arrays(self, timeline, n):
        """
        Initialise timeline arrays for TFV model.

        Notes
        -----
        Gas puff timeline mapped to burn signal.
        """
        self.DEMO_t = timeline["time"][:n]
        self.DEMO_rt = np.array(timeline["fusion_time"][:n])
        self.DT_rate = timeline["DT_rate"][:n]
        self.DD_rate = timeline["DD_rate"][:n]
        m_gas = T_MOLAR_MASS * raw_uc(self.params.m_gas, "Pa.m^3/s", "mol/s") / 1000
        self.grate = m_gas * self.DT_rate / max(self.DT_rate)
        self.bci = timeline["blanket_change_index"]
        # Burn rate of T [kgs of T per second]
        self.brate = (T_MOLAR_MASS / N_AVOGADRO / 1000) * self.DT_rate
        # T production rate from D-D reaction channel [kgs of T per second]
        self.prate = (T_MOLAR_MASS / N_AVOGADRO / 1000) * self.DD_rate / 2  # Only 50%!

    def seed_t(self):
        """
        Seed an initial value to the model.
        """
        self.m_T_start = 5.0
        self.m_T = [self.m_T_start]

    def tbreed(self, TBR, m_T_0):
        """
        Ideal system without T sequestration. Used for plotting and sanity.
        """
        m_T = m_T_0 * np.ones(len(self.DEMO_t))
        for i in range(1, len(self.DEMO_t)):
            dt = self.DEMO_t[i] - self.DEMO_t[i - 1]
            t_bred = TBR * self.brate[i] * (YR_TO_S * dt)
            t_bred += self.prate[i] * (YR_TO_S * dt)
            t_burnt = self.brate[i] * (YR_TO_S * dt)
            t_DD = self.prate[i] * (YR_TO_S * dt)
            m_T[i] = (m_T[i - 1]) * np.exp(-T_LAMBDA * dt) - t_burnt + t_bred + t_DD
        return m_T

    def plasma(self, eta_iv, max_inventory, flows=None):
        """
        In-vessel environment

        Parameters
        ----------
        eta_iv: 0 <= float <= 1
            In-vessel accumulation efficiency

        max_inventory: float
            Tnventory limit of in-vessel environment [kg]
            (e.g. 0.7 kg in ITER in-vessel)

        Returns
        -------
        m_out: np.array(N)
            Flow-rate out of the system [kg/s]
        """
        plasma = FuelCycleComponent(
            "Plasma",
            self.DEMO_t,
            eta_iv,
            max_inventory,
            bci=self.bci,
            retention_model="sqrt_bathtub",
            summing=False,
        )
        for flow in flows:
            plasma.add_in_flow(flow)
        plasma.run()
        self.I_plasma = plasma.inventory
        return plasma.m_out

    def blanket(self, eta_b, max_inventory):
        """
        The tritium breeding system. Dumps stored inventory at blanket change.

        Parameters
        ----------
        eta_b: float
            The retention efficiency parameter for the blanket
        max_inventory: float
            The maximum inventory in the blanket

        Returns
        -------
        m_out: array_like
            Flow-rate out of the system [kg/s]
        """
        m_T_bred = self.params.TBR * self.brate
        blanket = FuelCycleComponent(
            "Blanket", self.DEMO_t, eta_b, max_inventory, bci=self.bci, summing=True
        )
        blanket.add_in_flow(m_T_bred)
        blanket.run()
        self.M_T_bred = blanket.sum_in
        self.I_blanket = blanket.inventory
        return blanket.m_out

    def tfv(self, eta_tfv, flows):
        """
        The TFV system where the tritium flows from the BB and plasma are combined.

        Parameters
        ----------
        eta_tfv: float
            Detritiation factor of the system
        flows: list(np.array(N), ..)
            The flows to be added to the TFV block

        Returns
        -------
        m_out: np.array(N)
            Flow-rate out of the system [kg/s]
        """
        # Runs in compressed time
        tfv = FuelCycleComponent(
            "TFV systems",
            self.t,
            eta_tfv,
            self.params.I_tfv_max,
            min_inventory=self.params.I_tfv_min,
            retention_model="fountaintub",
        )
        for flow in flows:
            tfv.add_in_flow(flow)
        tfv.run()
        m_tfv_out = FuelCycleFlow(self.t, tfv.m_out, 0)
        self.I_tfv = tfv.inventory
        # Exhaust processing
        m_in_isotope_re, m_in_exhaust_det = m_tfv_out.split(2, [self.params.f_exh_split])
        # Isotope rebalancing
        # Storage and Gas Distribution and Control are the same for me
        # Fließt direkt zum Injektor
        # Exhaust detritiation
        # Combines Water Detritiation and Isotope Separation
        m_in_exhaust_det = FuelCycleFlow(self.t, m_in_exhaust_det, self.params.t_detrit)
        m_exh_stor, m_ex_stack = m_in_exhaust_det.split(2, [self.params.f_detrit_split])
        return m_in_isotope_re + m_exh_stor, m_ex_stack

    def stack(self, flows):
        """
        Exhaust to environment
        """
        stack = FuelCycleComponent(
            "Stack", self.t, 0, float("inf"), retention_model="bathtub", summing=True
        )
        for flow in flows:
            stack.add_in_flow(flow)
        stack.run()
        self.I_stack = stack.inventory
        # Total release to the environment
        self.M_T_stack = stack.sum_in

    def injector(self, flows):
        """
        Pellet injection system assumed
        """
        injector = FuelCycleComponent("Injector", self.t, 1, 0)
        for flow in flows:
            if flow is not None:
                injector.add_in_flow(flow)
        injector.run()
        return injector.m_out

    def recycle(self):
        """
        The main loop of the fuel cycle, which is called recusively until the
        convergence criterion is met
        """
        # Fuelling (fuel in)
        # Fuel pump built in (ghosted component)
        self.m_T_in = self.brate / (self.params.f_b * self.params.eta_f)
        # m_T_out = (1/self.f_b-1)*self.brate
        # In-vessel flow lost from fuelling lines as gas (does not enter core)
        iv_loss_flow = (
            (1 - self.params.eta_fuel_pump) * (1 - self.params.eta_f) * self.m_T_in
        )
        # Gas puff flow
        gpuff = self.grate

        # Plasma/in-vessel block

        flows = [
            self.brate / self.params.f_b,
            iv_loss_flow,
            gpuff,
            self.prate,  # D-D T production from plasma
            -self.brate,
        ]

        m_T_out = self.plasma(self.params.eta_iv, self.params.I_miv, flows=flows)
        # Resolution - Not used everywhere for speed
        n_ts = int(round((YR_TO_S * self.DEMO_t[-1]) / self.timestep))
        self.t, m_pellet_in = discretise_1d(self.DEMO_t, self.m_T_in, n_ts)

        # Flow out of the vacuum vessel
        t, m_T_out = discretise_1d(self.DEMO_t, m_T_out, n_ts)
        # Direct Internal Recycling
        m_plasma_out = FuelCycleFlow(t, m_T_out, 0)  # Initialise flow 0 t

        m_direct, m_indirect = m_plasma_out.split(2, [self.params.f_dir])
        # DIR separation
        # Flow 9
        direct = FuelCycleFlow(t, m_direct, self.params.t_pump)
        # Flow 10 with (time delay t_10+t_11/12)
        indirect = FuelCycleFlow(t, m_indirect, self.params.t_pump + self.params.t_exh)
        # Blanket
        m_T_bred = self.blanket(self.params.eta_bb, self.params.I_mbb)
        t, m_bred = discretise_1d(self.DEMO_t, m_T_bred, n_ts)
        m_T_bred = FuelCycleFlow(t, m_bred, self.params.t_ters.value)
        # Tritium extraction and recovery system + coolant water purification
        m_T_bred_totfv, m_T_bred_tostack = m_T_bred.split(2, [self.params.f_terscwps])
        # TFV systems - runs in t
        m_tfv_out, m_tfv_stack = self.tfv(self.params.eta_tfv, flows=[indirect.out_flow])
        # Release to environment
        self.stack([m_T_bred_tostack, m_tfv_stack])
        m_tfv_out = FuelCycleFlow(t, m_tfv_out, 0)
        # Store
        store = FuelCycleComponent("Store", t, 1, np.inf)
        # Flow 11+13
        store.add_in_flow(m_tfv_out.out_flow)
        # Flow 16
        store.add_in_flow(m_T_bred_totfv)
        # Pump which compensates fuelling efficiency loss in pellet
        # injection flight tubes (Flow 3)
        store.add_in_flow(
            m_pellet_in * (1 - self.params.eta_f) * self.params.eta_fuel_pump
        )
        # Flow 9
        store.add_in_flow(direct.out_flow)
        _, gpuff_corr = discretise_1d(self.DEMO_t, gpuff, n_ts)
        # store.add_in_flow(-gpuff_corr)
        store.run()
        # This is conservative... need to find a way to make gas available
        # instantaneously. At present this means gas puffs get "frozen" first
        m_store = FuelCycleFlow(t, store.m_out, self.params.t_freeze).out_flow
        # Add a correction flow for instantaneous gas puffing

        # m_store += gpuff_corr
        # Fuelling requirements
        # Adds gas flow now (not accounted for in ghosted fuel
        # line pumps)
        _, m_in = discretise_1d(self.DEMO_t, self.m_T_in + gpuff, n_ts)
        # Completes the loop in numba
        m_T = _speed_recycle(self.m_T_start, t, m_in, m_store)
        self.m_T = m_T + self.params.I_tfv_min  # !!!!

        min_tritium = np.min(m_T)
        self.m_T_req = self.m_T_start - min_tritium

        while abs(self.m_T_req - self.m_T_start) / self.m_T_req > self.conv_thresh:
            # Recursively called until start-up inventory is roughly equal to
            # the initial seeded (and re-calculated) value. This is important
            # to accurately calculate decay losses (which are a function of
            # mass)

            self.iterations += 1
            if self.verbose:
                old_m_start = self.m_T_start + self.params.I_tfv_min
                new_m_start = self.m_T_start - min_tritium + self.params.I_tfv_min
                bluemira_print(
                    f"m_T_start old: {old_m_start:.2f} kg \n"
                    f"m_T_start new: {new_m_start:.2f}"
                    f" kg\niterations: {self.iterations}"
                )
            self.m_T_start -= min_tritium
            self.recycle()

    def plot(self):
        """
        Plot the results of the fuel cycle model.
        """
        _, ax = plt.subplots(2, 1)
        self.plot_m_T(ax=ax[0])
        self.plot_inventory(ax=ax[1])

    def plot_m_T(self, **kwargs):
        """
        Plot the evolution of the tritium masses over time.
        """
        ax = kwargs.get("ax", plt.gca())
        ax.plot(
            self.DEMO_t,
            self.tbreed(self.params.TBR, self.m_T_req),
            label="Total T inventory",
        )

        (c,) = ax.plot(
            self.t[self.max_T[0]],
            self.max_T[1],
            label="Total unsequestered T inventory",
        )
        ax.plot(
            self.t,
            self.m_T,
            color="gray",
            alpha=0.8,
            linewidth=0.1,
            label="Unsequestered T inventory in stores",
        )
        ax.plot(self.t[self.max_T[0]], self.max_T[1], color=c.get_color())
        leg = ax.legend()
        for line in leg.get_lines():
            line.set_linewidth(3)
            line.set_alpha(1)
        ax.set_ylabel("$m_{{T}}$ [kg]")
        if "ax" not in kwargs:
            ax.set_xlabel("Elapsed plant lifetime [years]")
        ax.annotate(
            "$m_{T_{start}}$",
            xy=[0, self.m_T_req],
            xytext=[1, self.m_T_req + 4],
            arrowprops=dict(headwidth=0.5, width=0.5, facecolor="k", shrink=0.1),
        )

        if np.isfinite(self.t_d):
            if self.t_d < 0.8 * self.DEMO_t[-1]:
                s = 1
            else:
                s = -1.5
            ax.annotate(
                "$t_{d}$",
                xy=[self.t_d, 0],
                xytext=[self.t_d + s, 4],
                arrowprops=dict(headwidth=0.5, width=0.5, facecolor="k", shrink=0.1),
            )
            if self.arg_t_d is not None:
                self._plot_t_d(ax=ax)
        else:
            ax.annotate("$t_{d}=\\infty$", xy=[self.t[-1] - 3, 2])

        if np.isfinite(self.t_infl):
            if self.t_d < 0.8 * self.DEMO_t[-1]:
                s = 1
            else:
                s = 1.5
            ax.annotate(
                "$t_{infl}$",
                xy=[self.t_infl, 0],
                xytext=[self.t_infl + s, 2],
                arrowprops=dict(headwidth=0.5, width=0.5, facecolor="k", shrink=0.1),
            )
            if self.arg_t_infl is not None:
                self._plot_t_infl(self.arg_t_infl, ax=ax)

        ax.set_xlim([0, self.t[-1]])
        ax.set_ylim(bottom=0)

        return ax

    def plot_inventory(self, **kwargs):
        """
        Plot the evolution of the tritium inventories (including sequestered)
        over time.
        """
        ax = kwargs.get("ax", plt.gca())
        chop = -2

        inventory = self._adjust_inv_plot(self.DEMO_t[:chop], self.I_plasma[:chop])
        ax.plot(self.DEMO_t[:chop], inventory, label="In-vessel")
        inventory = self._adjust_inv_plot(self.DEMO_t[:chop], self.I_blanket[:chop])

        ax.plot(self.DEMO_t[:chop], inventory, label="Blanket")
        ax.plot(self.t[:chop], self.I_tfv[:chop], label="TFV systems")
        # ax.plot(self.t[:chop], self.I_stack[:chop],
        #        label='Environment')
        ax.legend(bbox_to_anchor=[0.99, 0.89])
        if "ax" not in kwargs:
            ax.set_title("Trapped T [kg]")
        ax.set_ylabel("$m_{{T}}$ [kg]")
        ax.set_xlabel("Elapsed plant lifetime [years]")
        ax.set_xlim(left=0)

    @staticmethod
    def _adjust_inv_plot(t, inventory, thresh=0.2):
        """
        Plot correction for compressed time inventories
        """
        idx = np.where(t - np.roll(t, 1) > thresh)[0] - 2
        inventory = inventory.copy()
        for i in idx:
            inventory[i + 1] = inventory[i]
        return inventory

    def calc_t_d(self):
        """
        Calculate the doubling time of a fuel cycle timeline, assuming that a future
        tokamak requires the same start-up inventory as the present one.

        Returns
        -------
        t_d: float
            Doubling time of the tritium fuel cycle [y]

        \t:math:`t_{d} = t[\\text{max}(\\text{argmin}\\lvert m_{T_{store}}-I_{TFV_{min}}-m_{T_{start}}\\rvert))]`
        """  # noqa :W505
        t_req = self.m_T[0] + self.params.I_tfv_min
        m_temp = self.m_T[::-1]
        try:
            arg_t_d_temp = next(i for i, v in enumerate(m_temp) if v < t_req)
        except StopIteration:
            # Technically, an infinte doubling time is correct here, however it
            # does make the database rather annoying to build reduced laws from
            # TODO: Consider another way...
            return None, float("Inf")
        else:
            arg_t_d = len(self.t) - arg_t_d_temp
            # Check a little around
            # TODO: This single line of code is now the worst offender (0.066s)
            if True not in [x > t_req for x in self.m_T[arg_t_d - 10 : arg_t_d + 10]]:
                return None, float("Inf")
        try:
            return arg_t_d, self.t[arg_t_d]
        except IndexError:
            return arg_t_d - 1, self.t[-1]

    def calc_t_infl(self):
        """
        Calculate the inflection time of the reactor tritium inventory
        """
        arg_t_infl = np.argmin(self.m_T)
        return arg_t_infl, self.t[arg_t_infl]

    def _plot_t_d(self, **kwargs):
        ax = kwargs.get("ax", plt.gca())
        next(ax._get_lines.prop_cycler)
        vlinex = [self.t_d, self.t_d]
        vliney = [0, self.m_T[0] + self.params.I_tfv_min]
        (c,) = ax.plot(
            self.t_d, self.m_T[0] + self.params.I_tfv_min, marker="o", markersize=10
        )
        ax.plot(vlinex, vliney, color=c.get_color(), linestyle="--")

    def _plot_t_infl(self, arg, **kwargs):
        ax = kwargs.get("ax", plt.gca())
        next(ax._get_lines.prop_cycler)
        vlinex = [self.t[arg], self.t[arg]]
        vliney = [0, self.m_T[arg]]
        (c,) = ax.plot(self.t[arg], self.m_T[arg], marker="o", markersize=10)
        ax.plot(vlinex, vliney, color=c.get_color(), linestyle="--")

    def calc_m_release(self):
        """
        Calculate the tritium release rate from the entire system to the environment.

        Returns
        -------
        release_rate: float
            Tritium release rate [g/yr]
        """
        max_load_factor = find_max_load_factor(self.DEMO_t, self.DEMO_rt)
        mb = 1000 * max(self.brate)
        m_gas = 1000 * max(self.grate)
        return legal_limit(
            max_load_factor,
            self.params.f_b,
            m_gas,
            self.params.eta_f,
            self.params.eta_fuel_pump,
            self.params.f_dir,
            self.params.f_exh_split,
            self.params.f_detrit_split,
            self.params.f_terscwps,
            self.params.TBR,
            mb=mb,
        )

    def sanity(self):
        """
        Check that no tritium is lost (graphically).
        """
        f, ax = plt.subplots()
        m_ideal = self.tbreed(self.params.TBR, self.m_T_req)
        inter = interp1d(self.DEMO_t, self.I_blanket)
        bb_inventory = inter(self.t)
        inter = interp1d(self.DEMO_t, self.I_plasma)
        pl_inventory = inter(self.t)
        m_tritium = (
            self.m_T
            + bb_inventory
            + pl_inventory
            + self.I_tfv
            - self.params.I_tfv_min
            + self.I_stack
        )
        ax.plot(self.t, m_tritium, label="max with sequestered")
        ax.plot(self.DEMO_t, m_ideal, label="ideal")
        ax.plot(self.t[self.max_T[0]], self.max_T[1], label="max yellow")
        ax.legend()
