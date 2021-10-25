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


@dataclass
class PlotOptions(abc.ABC):
    """
    The options that are available for plotting objects in 3D
    """

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
        api: str = None,
    ):
        self.options = options
        self._plot_func = get_module(api).plot

    @property
    def options(self) -> PlotOptions:
        """
        The options that will be used to plot the object.
        """
        return self._options

    @options.setter
    @abc.abstractmethod
    def options(self, val: PlotOptions) -> None:
        self._options = PlotOptions() if val is None else val

    @abc.abstractmethod
    def plot(self, obj, options: Optional[PlotOptions] = None, *args, **kwargs) -> None:
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
        return self._plot_func(obj, options, *args, **kwargs)


class Plottable:
    """
    Mixin class to make a class plottable by imparting a plot method and options.

    The implementing class must set the _plotter attribute to an instance of the
    appropriate Plotter class.
    """

    _plotter: Plotter = None

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
