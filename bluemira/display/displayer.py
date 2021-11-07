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
api for plotting using freecad
"""
from __future__ import annotations

# import typing
from typing import List, Optional, Union

# import errors
from .error import DisplayError

# import visualisation
from ..geometry import _freecadapi

import bluemira as bluemira
import bluemira.geometry as geo

import pprint
import copy
from abc import ABC, abstractmethod

DEFAULT_DISPLAY_OPTIONS = {
    "color": (0.5, 0.5, 0.5),
    "transparency": 0.0,
}


def get_default_options():
    """
    Returns the default display options.
    """
    return copy.deepcopy(DEFAULT_DISPLAY_OPTIONS)


class DisplayOptions:
    """
    The options that are available for displaying objects.
    """

    _options = None

    def as_dict(self):
        """
        Returns the instance as a dictionary.
        """
        return copy.deepcopy(self._options)

    def modify(self, **kwargs):
        """
        Function to override plotting options.
        """
        if kwargs:
            for k in kwargs:
                if k in self._options:
                    self._options[k] = kwargs[k]

    def __repr__(self):
        """
        Representation string of the DisplayOptions.
        """
        return f"{self.__class__.__name__}({pprint.pformat(self._options)}" + "\n)"

# =======================================================================================
# Visualisation
# =======================================================================================
class DisplayCADOptions(DisplayOptions):
    """
    The options that are available for displaying objects in 3D
    Parameters
    ----------
    color: Tuple[float, float, float]
        The RBG colour to display the object, by default (0.5, 0.5, 0.5).
    transparency: float
        The transparency to display the object, by default 0.0.
    """

    def __init__(self, **kwargs):
        self._options = get_default_options()
        if kwargs:
            for k in kwargs:
                if k in self._options:
                    self._options[k] = kwargs[k]
        # TODO: in this way class attributes are not seen till runtime. Not sure if
        #  this should be changed manually declaring all the attributes.
        for k in self._options:
            setattr(self, k, self._options[k])

    def as_dict(self):
        return self._options


def _get_displayer_class(part):
    """
    Get the displayer class for an object.
    """
    if isinstance(part, bluemira.base.components.Component):
        plot_class = ComponentDisplayer
    else:
        raise DisplayError(
            f"{part} object cannot be displayed. No Displayer available for {type(part)}"
        )
    return plot_class


def _validate_display_inputs(parts, options):
    """
    Validate the lists of parts and options, applying some default options.
    """
    if not isinstance(parts, list):
        parts = [parts]

    if options is None:
        options = [None] * len(parts)
    elif not isinstance(options, list):
        options = [options] * len(parts)

    if len(options) != len(parts):
        raise DisplayError(
            "If options for plot are provided then there must be as many options as "
            "there are parts to plot."
        )
    return parts, options


def show_cad(
    parts: Union[geo.base.BluemiraGeo, List[geo.base.BluemiraGeo]],
    options: Optional[Union[DisplayCADOptions, List[DisplayCADOptions]]] = None,
    **kwargs,
):
    """
    The implementation of the display API for FreeCAD parts.

    Parameters
    ----------
    parts: Union[Part.Shape, List[Part.Shape]]
        The parts to display.
    options: Optional[Union[_PlotCADOptions, List[_PlotCADOptions]]]
        The options to use to display the parts.
    """
    parts, options = _validate_display_inputs(parts, options)

    new_options = []
    for o in options:
        if isinstance(o, DisplayCADOptions):
            temp = DisplayCADOptions(**o.as_dict())
            temp.modify(**kwargs)
            new_options.append(temp)
        else:
            temp = DisplayCADOptions(**kwargs)
            new_options.append(temp)

    shapes = [part._shape for part in parts]
    freecad_options = [o.as_dict() for o in new_options]

    _freecadapi.show_cad(shapes, freecad_options)


class BaseDisplayer(ABC):
    _CLASS_DISPLAY_OPTIONS = {}

    def __init__(self, options: Optional[DisplayCADOptions] = None, **kwargs):
        self.options = (
            DisplayCADOptions(**self._CLASS_PLOT_OPTIONS) if options is None else options
        )
        self.options.modify(**kwargs)

    @abstractmethod
    def show_cad(self, objs, **kwargs):
        pass


class ComponentDisplayer(BaseDisplayer):
    """
    CAD displayer for Components
    """

    def show_cad(self, comp, **kwargs):
        self._shapes = []
        self._options = []
        if comp.is_leaf:
            self._shapes.append(comp.shape)
            self._options.append(self.display_cad_options)
        else:
            for child in comp.children:
                self._shapes.append(child.shape)
                self._options.append(child.display_cad_options)
        show_cad(self._shapes, self._options, **kwargs)


class DisplayableCAD:
    """
    Mixin class to make a class displayable by imparting a plotcad method and options.

    Notes
    -----
    The implementing class must set the _plottercad attribute to an instance of the
    appropriate Displayer class.
    """

    def __init__(self):
        super().__init__()
        self._display_cad_options: DisplayCADOptions = DisplayCADOptions()

    @property
    def display_cad_options(self) -> DisplayCADOptions:
        """
        The options that will be used to display the object.
        """
        return self._display_cad_options

    @display_cad_options.setter
    def display_cad_options(self, value: DisplayCADOptions):
        if not isinstance(value, DisplayCADOptions):
            raise DisplayError(
                "Display options must be set to a PlotOptions instance."
            )
        self._display_cad_options = value

    @property
    def _displayer(self) -> BaseDisplayer:
        """
        The options that will be used to display the object.
        """
        return _get_displayer_class(self)(self._display_cad_options)

    def show_cad(self, **kwargs) -> None:
        """
        Default method to call display the object by calling into the Displayer's display
        method.

        Returns
        -------
        axes
            The axes that the plot has been displayed onto.
        """
        return self._displayer.show_cad(self, **kwargs)
