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

"""
api for plotting using CAD backend
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict
from enum import Enum
from typing import List, Optional, Union

from bluemira.base.look_and_feel import bluemira_debug
from bluemira.display.error import DisplayError
from bluemira.display.palettes import BLUE_PALETTE
from bluemira.display.plotter import DisplayOptions
from bluemira.utilities.tools import get_module


class ViewerBackend(Enum):
    """CAD viewer backends."""

    FREECAD = "bluemira.codes._freecadapi"
    POLYSCOPE = "bluemira.codes._polyscope"


def get_default_options(backend=ViewerBackend.FREECAD):
    """
    Returns the default display options.
    """
    return get_module(backend.value).DefaultDisplayOptions()


class DisplayCADOptions(DisplayOptions):
    """
    The options that are available for displaying objects in 3D

    Parameters
    ----------
    backend
        the backend viewer being used
    """

    __slots__ = ("_options",)

    def __init__(self, backend=ViewerBackend.FREECAD, **kwargs):
        self._options = get_default_options(backend)
        self.modify(**kwargs)

    def __setattr__(self, attr, val):
        """
        Set attributes in options dictionary
        """
        if (
            hasattr(self, "_options")
            and self._options is not None
            and attr in self._options.__annotations__
        ):
            setattr(self._options, attr, val)
        else:
            super().__setattr__(attr, val)

    def __getattribute__(self, attr):
        """
        Get attributes or from "_options" dict
        """
        try:
            return super().__getattribute__(attr)
        except AttributeError as ae:
            if attr != "_options":
                try:
                    return getattr(self._options, attr)
                except AttributeError:
                    raise ae
            else:
                raise ae

    def modify(self, **kwargs):
        """Modify options"""
        for k, v in kwargs.items():
            setattr(self, k, v)

    def as_dict(self):
        """
        Returns the instance as a dictionary.
        """
        return asdict(super().as_dict())


# =======================================================================================
# Visualisation
# =======================================================================================


def _validate_display_inputs(parts, options):
    """
    Validate the lists of parts and options, applying some default options.
    """
    if parts is None:
        bluemira_debug("No new parts to display")
        return [], []

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
    parts: Optional[Union[BluemiraGeo, List[BluemiraGeo]]] = None,  # noqa: F821
    options: Optional[Union[DisplayCADOptions, List[DisplayCADOptions]]] = None,
    backend: Union[str, ViewerBackend] = ViewerBackend.FREECAD,
    **kwargs,
):
    """
    The CAD display API.

    Parameters
    ----------
    parts
        The parts to display.
    options
        The options to use to display the parts.
    backend
        Viewer backend
    kwargs
        Passed on to modifications to the plotting style options and backend
    """
    if isinstance(backend, str):
        backend = ViewerBackend[backend.upper()]

    parts, options = _validate_display_inputs(parts, options)

    new_options = []
    for o in options:
        if isinstance(o, DisplayCADOptions):
            temp = DisplayCADOptions(**o.as_dict(), backend=backend)
            temp.modify(**kwargs)
            new_options.append(temp)
        else:
            new_options.append(DisplayCADOptions(**kwargs, backend=backend))

    part_options = [o.as_dict() for o in new_options]

    get_module(backend.value).show_cad(parts, part_options, **kwargs)


class BaseDisplayer(ABC):
    """
    Displayer abstract class
    """

    _CLASS_DISPLAY_OPTIONS = {}

    def __init__(self, options: Optional[DisplayCADOptions] = None, **kwargs):
        self.options = (
            DisplayCADOptions(**self._CLASS_DISPLAY_OPTIONS)
            if options is None
            else options
        )
        self.options.modify(**kwargs)

    @abstractmethod
    def show_cad(self, objs, **kwargs):
        """
        Display a CAD object
        """
        pass


def _get_displayer_class(part):
    """
    Get the displayer class for an object.
    """
    import bluemira.base.components

    if isinstance(part, bluemira.base.components.Component):
        plot_class = ComponentDisplayer
    else:
        raise DisplayError(
            f"{part} object cannot be displayed. No Displayer available for {type(part)}"
        )
    return plot_class


class DisplayableCAD:
    """
    Mixin class to make a class displayable by imparting a show_cad method and options.
    """

    def __init__(self):
        super().__init__()
        self._display_cad_options: DisplayCADOptions = DisplayCADOptions()
        self._display_cad_options.colour = next(BLUE_PALETTE)

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
                "Display options must be set to a DisplayCADOptions instance."
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


class ComponentDisplayer(BaseDisplayer):
    """
    CAD displayer for Components
    """

    def show_cad(
        self,
        comps,
        **kwargs,
    ):
        """
        Display the CAD of a component or iterable of components

        Parameters
        ----------
        comp: Union[Iterable[Component], Component]
            Component, or iterable of Components, to be displayed
        """
        import bluemira.base.components as bm_comp

        show_cad(
            *bm_comp.get_properties_from_components(
                comps, ("shape", "display_cad_options")
            ),
            **kwargs,
        )
