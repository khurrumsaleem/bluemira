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
api for plotting using matplotlib
"""
from typing import Optional, Union, List

import bluemira.geometry as geo
import bluemira.plotting as plotting
from bluemira.geometry.base import BluemiraGeo
from bluemira.base.plot import PlotOptions
from bluemira.base.error import PlotError


def plot(
    parts: Union[BluemiraGeo, List[BluemiraGeo]],
    options: Optional[Union[PlotOptions, List[PlotOptions]]] = None,
):
    """
    The implementation of the display API for FreeCAD parts.

    Parameters
    ----------
    parts: Union[Part.Shape, List[Part.Shape]]
        The parts to display.
    options: Optional[Union[PlotOptions, List[PlotOptions]]]
        The options to use to display the parts.
    """
    print(f"Plot options: {options}")
    if not isinstance(parts, list):
        parts = [parts]

    if options is None:
        options = [PlotOptions()] * len(parts)
    elif not isinstance(options, list):
        options = [options] * len(parts)

    if len(options) != len(parts):
        raise PlotError(
            "If options for plot are provided then there must be as many options as "
            "there are parts to plot."
        )

    ax = None
    for part, option in zip(parts, options):
        if isinstance(part, geo.wire.BluemiraWire):
            plotter = plotting.plotter.WirePlotter(
                **option.options, ndiscr=100, byedges=True
            )
        elif isinstance(part, geo.face.BluemiraFace):
            plotter = plotting.plotter.FacePlotter(
                **option.options, ndiscr=100, byedges=True
            )
        else:
            raise PlotError(
                f"{part} object cannot be plotted. No Plotter available for {type(part)}"
            )
        ax = plotter(part, ax, False, False, ndiscr=100, byedges=True)

    plotter.show_plot()
