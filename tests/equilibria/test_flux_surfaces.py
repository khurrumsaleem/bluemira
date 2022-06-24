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

import os

import numpy as np
import pytest

from bluemira.base.file import get_bluemira_path
from bluemira.equilibria import Equilibrium
from bluemira.equilibria.error import FluxSurfaceError
from bluemira.equilibria.find import find_flux_surface_through_point
from bluemira.equilibria.flux_surfaces import (
    ClosedFluxSurface,
    FieldLineTracer,
    OpenFluxSurface,
    PartialOpenFluxSurface,
    poloidal_angle,
)
from bluemira.equilibria.shapes import flux_surface_cunningham, flux_surface_johner
from bluemira.geometry._deprecated_loop import Loop

TEST_PATH = get_bluemira_path("equilibria/test_data", subfolder="tests")


class TestOpenFluxSurfaceStuff:
    @classmethod
    def setup_class(cls):
        eq_name = "eqref_OOB.json"
        filename = os.sep.join([TEST_PATH, eq_name])
        cls.eq = Equilibrium.from_eqdsk(filename)

    def test_bad_geometry(self):
        closed_loop = Loop(x=[0, 4, 5, 8, 0], z=[1, 2, 3, 4, 1])
        with pytest.raises(FluxSurfaceError):
            _ = OpenFluxSurface(closed_loop)
        with pytest.raises(FluxSurfaceError):
            _ = PartialOpenFluxSurface(closed_loop)

    def test_connection_length(self):
        """
        Use both a flux surface and field line tracing approach to calculate connection
        length and check they are the same or similar.
        """
        x_start, z_start = 12, 0
        x_loop, z_loop = find_flux_surface_through_point(
            self.eq.x,
            self.eq.z,
            self.eq.psi(),
            x_start,
            z_start,
            self.eq.psi(x_start, z_start),
        )
        fs = OpenFluxSurface(Loop(x=x_loop, z=z_loop))
        lfs, hfs = fs.split(self.eq.get_OX_points()[0][0])
        l_lfs = lfs.connection_length(self.eq)
        l_hfs = hfs.connection_length(self.eq)

        # test discretisation sensitivity
        lfs_loop = lfs.loop.copy()
        lfs_loop.interpolate(3 * len(lfs_loop))
        lfs_interp = PartialOpenFluxSurface(lfs_loop)
        l_lfs_interp = lfs_interp.connection_length(self.eq)
        assert np.isclose(l_lfs, l_lfs_interp, rtol=5e-3)

        hfs_loop = hfs.loop.copy()
        hfs_loop.interpolate(3 * len(hfs_loop))
        hfs_interp = PartialOpenFluxSurface(hfs_loop)
        l_hfs_interp = hfs_interp.connection_length(self.eq)
        assert np.isclose(l_hfs, l_hfs_interp, rtol=5e-3)

        # compare with field line tracer
        flt = FieldLineTracer(self.eq)
        l_flt_lfs = flt.trace_field_line(x_start, z_start, n_turns_max=20, forward=True)
        l_flt_hfs = flt.trace_field_line(
            x_start, z_start, n_turns_max=20, forward=False
        ).connection_length
        print(len(l_flt_lfs.loop))
        assert np.isclose(l_flt_lfs.connection_length, l_lfs, rtol=2e-2)
        assert np.isclose(l_flt_hfs, l_hfs, rtol=2e-2)


class TestClosedFluxSurface:
    def test_bad_geometry(self):
        open_loop = Loop(x=[0, 4, 5, 8], z=[1, 2, 3, 4])
        with pytest.raises(FluxSurfaceError):
            _ = ClosedFluxSurface(open_loop)

    def test_symmetric(self):
        kappa = 1.5
        delta = 0.4
        fs = flux_surface_cunningham(7, 0, 1, kappa, delta, n=1000)
        fs.close()
        fs = ClosedFluxSurface(fs)
        assert np.isclose(fs.kappa, kappa)
        assert np.isclose(fs.kappa_lower, kappa, rtol=1e-2)
        assert np.isclose(fs.kappa_upper, kappa, rtol=1e-2)
        assert np.isclose(fs.delta_lower, fs.delta_upper, rtol=1e-2)
        assert np.isclose(fs.zeta_lower, fs.zeta_upper)

    def test_johner(self):

        R_0, z_0, a, kappa_u, kappa_l, delta_u, delta_l, a1, a2, a3, a4 = (
            7,
            0,
            2,
            1.9,
            1.6,
            0.4,
            0.33,
            -20,
            5,
            60,
            30,
        )
        fs = flux_surface_johner(
            7, 0, 2, kappa_u, kappa_l, delta_u, delta_l, a1, a2, a3, a4, n=1000
        )
        fs.close()
        fs = ClosedFluxSurface(fs)
        assert np.isclose(fs.major_radius, R_0)
        assert np.isclose(fs._z_centre, z_0)
        assert np.isclose(fs.minor_radius, a)
        assert np.isclose(fs.kappa, np.average([kappa_l, kappa_u]))
        assert np.isclose(fs.kappa_upper, kappa_u)
        assert np.isclose(fs.kappa_lower, kappa_l)
        assert np.isclose(fs.delta, np.average([delta_l, delta_u]))
        assert np.isclose(fs.delta_upper, delta_u)
        assert np.isclose(fs.delta_lower, delta_l)
        assert not np.isclose(fs.zeta_upper, fs.zeta_lower)


class TestFieldLine:
    @classmethod
    def setup_class(cls):
        eq_name = "eqref_OOB.json"
        filename = os.sep.join([TEST_PATH, eq_name])
        cls.eq = Equilibrium.from_eqdsk(filename)

    def test_connection_length(self):
        flt = FieldLineTracer(self.eq)
        field_line = flt.trace_field_line(13, 0, n_points=1000)
        assert np.isclose(
            field_line.connection_length, field_line.loop.length, rtol=5e-2
        )


def test_poloidal_angle():
    eq_name = "DN-DEMO_eqref.json"
    filename = os.path.join(TEST_PATH, eq_name)
    eq = Equilibrium.from_eqdsk(filename)
    # Building inputs
    x_strike = 10.0
    z_strike = -7.5
    Bp_strike = eq.Bp(x_strike, z_strike)
    Bt_strike = eq.Bt(x_strike)
    # Glancing angle
    gamma = 5.0
    # Poloidal angle
    theta = poloidal_angle(Bp_strike, Bt_strike, gamma)
    assert theta > gamma
    # By hand, from a different calculation
    assert round(theta, 1) == 20.6
