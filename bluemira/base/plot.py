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
Module containing interfaces and basic implementation for 3D plotting functionality.
"""

import abc
import dataclasses
from dataclasses import dataclass, field
from typing import Optional, Dict, Union

from bluemira.base.error import PlotError
from bluemira.base.look_and_feel import bluemira_warn
from bluemira.utilities.tools import get_module


# DEFAULT = {}
# DEFAULT["flags"] = {"points": True, "wires": True, "faces": True}
# DEFAULT["poptions"] = {"s": 10, "facecolors": "blue", "edgecolors": "black"}
# DEFAULT["woptions"] = {"color": "black", "linewidth": "0.5"}
# DEFAULT["foptions"] = {"color": "red"}
# DEFAULT["plane"] = "xz"
# DEFAULT["palette"] = None


@dataclass
class PlotOptions:
    """
    The options that are available for plotting objects in 3D

    Parameters
    ----------
    flag_points: bool
        If true, points are plotted. By default True.
    flag_wires: bool
        if true, wires are plotted. By default True.
    flag_faces: bool
        if true, faces are plotted. By default True.
    poptions: Dict
        dictionary with matplotlib options for points. By default  {"s": 10,
        "facecolors": "blue", "edgecolors": "black"}
    woptions: Dict
        dictionary with matplotlib options for wires. By default {"color": "black",
        "linewidth": "0.5"}
    foptions: Dict
        dictionary with matplotlib options for faces. By default {"color": "red"}
    plane: [str, Plane]
        The plane on which the object is projected for plotting. As string, possible
        options are "xy", "xz", "yz". By default 'xz'.
    palette:
        palette
    """
    #
    # def __init__(self, **kwargs):
    #     self.options = DEFAULT.copy()
    #     if kwargs:
    #         for k in kwargs:
    #             if k in self.options:
    #                 self.options[k] = kwargs[k]

    flags: Dict = field(default_factory=lambda: {"points": True, "wires": True,
                                                 "faces": True})
    poptions: Dict = field(default_factory=lambda: {"s": 10, "facecolors": "blue",
                                                    "edgecolors": "black"})
    woptions: Dict = field(default_factory=lambda: {"color": "black",
                                                    "linewidth": "0.5"})
    foptions: Dict = field(default_factory=lambda: {"color": "red"})
    plane: str = "xz"
    palette: Union[str, None] = None
    ndiscr: int = 100
    byedges: bool = True

    @property
    def options(self):
        return dataclasses.asdict(self)


class Plotter(abc.ABC):
    """
    Abstract base class to handle plotting objects

    Parameters
    ----------
    options: Optional[PlotOptions]
        The options to use to Plot the object, by default None in which case the
        default values for the PlotOptions class are used.
    api: str
        The API to use for plotting. This must implement a plot method with
        signature (objs, options), where objs are the primitive 3D object to plot. By
        default uses the FreeCAD api at bluemira.geometry._freecadapi.
    """

    def __init__(
        self,
        options: Optional[PlotOptions] = None,
        api: str = "bluemira.plotting._matplotlib",
    ):
        self._options = PlotOptions() if options is None else options
        self._plot_func = get_module(api).plot

    @property
    def options(self) -> PlotOptions:
        """
        The options that will be used to plot the object.
        """
        return self._options

    @options.setter
    def options(self, val: PlotOptions) -> None:
        self._options = val

    @abc.abstractmethod
    def plot(self, obj, options: Optional[PlotOptions] = None) -> None:
        """
        Plot the object by calling the plot function within the API.

        Parameters
        ----------
        obj
            The object to plot
        options: Optional[PlotOptions]
            The options to use to plot the object, by default None in which case the
        default values for the PlotOptions class are used.
        """
        self._plot_func(obj, options)


class Plottable:
    """
    Mixin class to make a class plottable by imparting a plot method and options.

    The implementing class must set the _plotter attribute to an instance of the
    appropriate Plotter class.
    """

    _plotter: Plotter

    @property
    def plot_options(self) -> PlotOptions:
        """
        The options that will be used to plot the object.
        """
        return self._plotter.options

    @plot_options.setter
    def plot_options(self, value: PlotOptions):
        if not isinstance(value, PlotOptions):
            raise PlotError("Plot options must be set to a PlotOptions instance.")
        self._plotter.options = value

    def plot(self, options: Optional[PlotOptions] = None) -> None:
        """
        Default method to call plot the object by calling into the Plotter's plot
        method.

        Parameters
        ----------
        options: Optional[PlotOptions]
            If not None then override the object's plot_options with the provided
            options. By default None.
        """
        self._plotter.plot(self, options)


class BasicPlotter(Plotter):
    """
    A basic implementation of a Plotter that can plot provided primitive objects
    with the provided options.
    """

    def plot(self, obj, options: Optional[PlotOptions] = None) -> None:
        """
        Plot the primitive objects with the provided options.

        Parameters
        ----------
        obj
            The CAD primitive objects to be plotted.
        options: Optional[PlotOptions]
            The options to use to plot the primitives.
        """
        if options is None:
            options = self.options

        try:
            super().plot(obj, options)
        except Exception as e:
            bluemira_warn(f"Unable to plot object {obj} - {e}")
