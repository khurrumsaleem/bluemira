"""
Useful methods for multiple Power Cycle classes
"""

import matplotlib.pyplot as plt

# Import
import numpy as np


class PowerCycleUtilities:

    # ------------------------------------------------------------------
    # DATA MANIPULATION
    # ------------------------------------------------------------------
    @staticmethod
    def add_dict_entries(dictionary, new_entries):
        """
        Add (key,value) pairs to a dictionary, only if they are not
        already specified (i.e. no substitutions). If dictionary is
        empty, returns only `new_entries`.

        Parameters
        ----------
        dictionary: `dict`
            Dictionary to be modified.
        new_entries: `dict`
            Second dictionary, which entries will be added to
            `dictionary`, unless they already exist.

        Returns
        -------
        dictionary: `dict`
            Modified dictionary.
        """

        # Validate whether `dictionary` exists (i.e. not empty)
        if dictionary:

            # Keys of new entries
            new_entries_keys = new_entries.keys()

            # For each key
            for key in new_entries_keys:

                # Current entry value
                value = new_entries[key]

                # Add entry to dictionary, if not yet there
                dictionary.setdefault(key, value)
        else:

            # For empty `dictionary`, output only `new_entries`
            dictionary = new_entries

        # Output extended dictionary
        return dictionary

    # ------------------------------------------------------------------
    # PLOT MANIPULATION
    # ------------------------------------------------------------------
    @staticmethod
    def validate_axes(ax):
        """
        Validate axes argument for plotting method. If `None`, create
        new `axes` instance.
        """
        if ax is None:
            ax = plt.gca()
        elif not isinstance(ax, (plt.axes.Axes)):
            raise TypeError(
                """
                The argument 'ax' used to create a plot is not
                an instance of the `Axes` class.
                """
            )
        return ax

    @staticmethod
    def apply_plot_options(plot_obj, **kwargs):
        """
        Try to apply a set of plotting options for an input collection
        instance (from `matplotlib.collections`). If the attempt leads
        to an error, collect the option in a list.

        Parameters
        ----------
        plot_obj: `matplotlib.collections` subclass
            Instance of a subclass of the `matplotlib.collections`
            class.
        **kwargs = `dict`
            Options for the `scatter` method.

        Returns
        -------
        ignored: `list`
            All keys of the `kwargs` parameter that lead to an error.
        """

        # Preallocate list of ignored
        ignored = []

        # For each option in kwargs
        for option in kwargs.keys():

            # Retrieve option value
            value = kwargs[option]

            # Try to apply options
            try:

                # Set attribute to axes
                setattr(plot_obj, option, value)

            except (TypeError, AttributeError):

                # Add option to list of ignored options
                ignored.append(option)

        # Return the list of ignored options
        return ignored

    @classmethod
    def adjust_2d_graph_ranges(cls, x_frac=0.1, y_frac=0.1, ax=None):
        """ "
        Adjust x-axis and y-axis limits of a plot given an input `axes`
        instance (from `matplotlib.axes`) and the chosen fractional
        proportions.
        New lower limits will be shifted negatively by current range
        multiplied by the input proportion. New upper limits will be
        similarly shifted, but positevely.

        Parameters
        ----------
        x_frac: `float`
            Fractional number by which x-scale will be enlarged. By
            default, this fraction is set to 10%.
        x_frac: `float`
            Fractional number by which y-scale will be enlarged. By
            default, this fraction is set to 10%.
        ax: `Axes`
            Instance of the `matplotlib.axes.Axes` class. By default,
            the currently selected axes are used.
        """

        # Validate axes
        ax = cls.validate_axes(ax)

        # Tighten axes scales
        ax.axis("tight")

        # Axes to adjust
        all_axes = ["x", "y"]

        # For each axis
        for axis in all_axes:

            # Data for current axis (type, limits, fraction input)
            if axis == "x":
                type = ax.get_xscale()
                lim = ax.get_xlim()
                fraction = x_frac
            elif axis == "y":
                type = ax.get_yscale()
                lim = ax.get_ylim()
                fraction = y_frac

            # Retrieve explicit limits
            lim_lower = lim[0]
            lim_upper = lim[1]

            # Validate axis type
            if type == "linear":

                # Compute linear range
                range = lim_upper - lim_lower

                # Compute new limits
                lim_lower = lim_lower - fraction * range
                lim_upper = lim_upper + fraction * range

            elif type == "log":

                # Compute logarithmic range
                range = np.log10(lim_upper / lim_lower)

                # Compute new limits
                lim_lower = lim_lower / 10 ** (fraction * range)
                lim_upper = lim_upper * 10 ** (fraction * range)

            else:
                raise ValueError(
                    """
                    The "adjust_graph_ranges" method has not yet been
                    implemented for this scale type.
                    """
                )

            # Store new limits for current axis
            if axis == "x":
                x_lim = (lim_lower, lim_upper)
            elif axis == "y":
                y_lim = (lim_lower, lim_upper)

        # Apply new limits
        ax.set_xlim(x_lim)
        ax.set_ylim(y_lim)
