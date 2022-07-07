"""
Classes to create loads in the power cycle model.
"""
from typing import List, Union

# Import
import numpy as np
from scipy.interpolate import interp1d as imported_interp1d

from bluemira.power_cycle.base import PowerCycleABC as imported_abc
from bluemira.power_cycle.base import PowerCycleError as imported_error
from bluemira.power_cycle.base import PowerCycleUtilities as imported_utilities

# ######################################################################
# POWER DATA
# ######################################################################


class PowerData(imported_abc):
    """
    Data class to store a set of time and load vectors.

    Takes a pair of (time,data) vectors and creates a PowerData object
    used to build Power Loads objects to represent the time evolution
    of a given power in the plant.
    Instances of this class do not specify any dependence between the
    data points it stores, so no method is defined for calculating
    values (e.g. interpolation). Instead, this class should be called
    by specialized classes such as `PowerLoad`.

    Parameters
    ----------
    name: `str`
        Description of the `PowerData` instance.
    time: `int` | `float` | `list`[`int` | `float`]
        List of time values that define the PowerData. [s]
    data: `int` | `float` | `list`[`int` | `float`]
        List of power values that define the PowerData. [W]
    """

    # ------------------------------------------------------------------
    # CLASS ATTRIBUTES
    # ------------------------------------------------------------------

    # Plot defaults (arguments for `matplotlib.pyplot.scatter`)
    _plot_defaults = {
        "c": "k",  # Marker color
        "s": 100,  # Marker size
        "marker": "x",  # Marker style
    }

    # Plot text settings (for `matplotlib.pyplot.text`)
    _text_angle = 45  # rotation angle
    _ind_point = 0  # index of (time,data) point used for location

    # Error messages
    _errors = {
        "increasing": imported_error(
            "Value",
            """
                The `time` input used to create an instance of the
                %CLASS_NAME class must be an increasing list.
                """,
        ),
        "sanity": imported_error(
            "Value",
            """
                The attributes `data` and `time` of an instance of the
                %CLASS_NAME class must have the same length.
                """,
        ),
    }

    # ------------------------------------------------------------------
    # CONSTRUCTOR
    # ------------------------------------------------------------------
    def __init__(
        self,
        name,
        time: Union[int, float, List[Union[int, float]]],
        data: Union[int, float, List[Union[int, float]]],
    ):

        # Call superclass constructor
        super().__init__(name)

        # Validate inputs to be lists
        self.data = super()._validate_list(data)
        self.time = super()._validate_list(time)

        # Verify time is an increasing vector
        self._is_increasing(self.time)

        # Validate created instance
        self._sanity()

    @classmethod
    def _is_increasing(cls, input):
        """
        Validate an input for class instance creation to be an
        increasing list.
        """
        check_increasing = []
        for i in range(len(input) - 1):
            check_increasing.append(input[i] <= input[i + 1])

        if not all(check_increasing):
            cls._issue_error("increasing")
        return input

    def _sanity(self):
        """
        Validate that `data` and `time` attributes both have the same
        length, so that they univocally represent power values in time.
        """
        length_data = len(self.data)
        length_time = len(self.time)
        if length_data != length_time:
            self._issue_error("sanity")

    # ------------------------------------------------------------------
    # OPERATIONS
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # VISUALIZATION
    # ------------------------------------------------------------------

    def plot(self, ax=None, **kwargs):
        """
        Plot the points that define the `PowerData` instance.

        This method applies the `matplotlib.pyplot.scatter` imported
        method to the vectors that define the `PowerData` instance. The
        default options for this plot are defined as class attributes,
        but can be overridden.

        Parameters
        ----------
        ax: `Axes`
            Instance of the `matplotlib.axes.Axes` class. By default,
            the currently selected axes are used.
        **kwargs = `dict`
            Options for the `scatter` method.

        Returns
        -------
        plot_list: `list`
            List of plot objects created by the `matplotlib` package.
            The first element of the list is the plot object created
            using the `pyplot.scatter`, while the second element of the
            list is the plot object created using the `pyplot.text`
            method.
        """

        # Validate axes
        ax = imported_utilities.validate_axes(ax)

        # Retrieve default plot options
        default = self._plot_defaults

        # Set each default options in kwargs, if not specified
        kwargs = imported_utilities.add_dict_entries(kwargs, default)

        # Retrieve instance characteristics
        name = self.name
        time = self.time
        data = self.data

        # Preallocate output
        plot_list = []

        # Plot
        label = name + " (data)"
        plot_obj = ax.scatter(time, data, label=label, **kwargs)
        plot_list.append(plot_obj)

        # Add text to plot
        index = self._ind_point
        text = f"{name} (PowerData)"
        label = name + " (name)"
        angle = self._text_angle
        plot_obj = ax.text(time[index], data[index], text, label=label, rotation=angle)
        plot_list.append(plot_obj)

        # Return plot object
        return plot_list


# ######################################################################
# GENERIC POWER LOAD
# ######################################################################


class PowerLoad(imported_abc):
    """
    Generic representation of a power load.

    Defines a power load with a set of `PowerData` instances. Each
    instance must be accompanied by a `model` specification, used to
    compute additional values between data points. This enables the
    instance to compute time-dependent curves.

    Parameters
    ----------
    name: 'str'
        Description of the `PowerLoad` instance.
    load: `PowerData` | `list`[`PowerData`]
        Collection of instances of the `PowerData` class that define
        the `PowerLoad` object.
    model: `str` | `list[`str`]
        List of types of model that defines values between points
        defined in the `load` Attribute. Valid models include:
        - 'ramp'
        - 'step'
    """

    # ------------------------------------------------------------------
    # CLASS ATTRIBUTES
    # ------------------------------------------------------------------

    # Default number of points in each curve segment
    _n_points = 100

    # Plot defaults (arguments for `matplotlib.pyplot.plot`)
    _plot_defaults = {
        "c": "k",  # Line color
        "lw": 2,  # Line width
        "ls": "-",  # Line style
    }

    # Detailed plot defaults (arguments for `matplotlib.pyplot.plot`)
    _detailed_defaults = {
        "c": "k",  # Line color
        "lw": 1,  # Line width
        "ls": "--",  # Line style
    }

    # Plot text settings (for `matplotlib.pyplot.text`)
    _text_angle = 45  # rotation angle
    _ind_point = -1  # index of (time,data) point used for location

    # Implemented models (add model name here after implementation)
    _valid_models = ["ramp", "step"]

    # Error messages
    _errors = {
        "model": imported_error(
            "Value",
            """
                The argument given for the attribute `model` is not a
                valid value. Only the following models are currently
                implemented in class %CLASS_NAME: %_VALID_MODELS.
                """,
        ),
        "n_points": imported_error(
            "Value",
            """
                The argument given for `n_points` is not a valid value
                for plotting an instance of the %CLASS_NAME class. Only
                non-negative integers are accepted.
                """,
        ),
        "sanity": imported_error(
            "Value",
            """
                The attributes `load` and `model` of an instance of the
                %CLASS_NAME class must have the same length.
                """,
        ),
        "time": imported_error(
            "Type",
            """
                The `time` input used to create a curve with an instance
                of the %CLASS_NAME class must be numeric or a list of
                numeric values.
                """,
        ),
    }

    # ------------------------------------------------------------------
    # CONSTRUCTOR
    # ------------------------------------------------------------------
    def __init__(self, name, load, model):

        # Call superclass constructor
        super().__init__(name)

        # Validate inputs
        self.load = self._validate_load(load)
        self.model = self._validate_model(model)

        # Validate created instance
        self._sanity()

    @classmethod
    def _validate_load(cls, load):
        """
        Validate 'load' input to be a list of `PowerData` instances.
        """
        load = super()._validate_list(load)
        for element in load:
            PowerData._validate(element)
        return load

    @classmethod
    def _validate_model(cls, model):
        """
        Validate 'model' input to be a list of valid models options.
        """
        model = super()._validate_list(model)
        for element in model:
            if element not in cls._valid_models:
                cls._issue_error("model")
        return model

    def _sanity(self):
        """
        Validate instance to have `load` and `model` attributes of
        same length.
        """
        if not len(self.load) == len(self.model):
            self._issue_error("sanity")

    # ------------------------------------------------------------------
    # OPERATIONS
    # ------------------------------------------------------------------

    def __add__(self, other):
        """
        Addition of `PowerLoad` instances is a new `PowerLoad` instance
        with joined `load` and `model` attributes.
        """

        # Retrieve `load` attributes
        this_load = self.load
        other_load = other.load

        # Retrieve `model` attributes
        this_model = self.model
        other_model = other.model

        # Create and output `another`
        another_load = this_load + other_load
        another_model = this_model + other_model
        another_name = "Resulting PowerLoad"
        another = PowerLoad(another_name, another_load, another_model)
        return another

    @classmethod
    def _validate_time(cls, time):
        """
        Validate 'time' input to be a list of numeric values.
        """
        time = super()._validate_list(time)
        for element in time:
            if not isinstance(element, (int, float)):
                cls._issue_error("time")
        return time

    @classmethod
    def _single_curve(cls, powerdata, model, time):
        """
        This method applies the `scipy.interpolate.interp1d` imported
        method to a single instance of the `PowerData` class. The kind
        of interpolation is determined by the `model` input. Values are
        returned at the times specified in the `time` input, with any
        out-of-bound values set to zero.
        """

        # Validate `model`
        if model == "ramp":
            k = "linear"  # Linear interpolation
        elif model == "step":
            k = "previous"  # Previous-value interpolation
        else:
            cls._issue_error("model")

        # Define interpolation function
        x = powerdata.time
        y = powerdata.data
        b = False  # out-of-bound values do not raise error
        f = (0, 0)  # below-bounds/above-bounds values set to 0
        lookup = imported_interp1d(x, y, kind=k, fill_value=f, bounds_error=b)

        # Output interpolated curve
        curve = list(lookup(time))
        return curve

    def curve(self, time):
        """
        Create a curve by calculating power load values at the specified
        times.

        This method applies the `scipy.interpolate.interp1d` imported
        method to each `PowerData` object stored in the `data` attribute
        and sums the results. The kind of interpolation is determined by
        each respective value in the `model` attribute. Any out-of-bound
        values are set to zero.

        Parameters
        ----------
        time: `list`[`float`]
            List of time values. [s]

        Returns
        -------
        curve: `list`[`float`]
            List of power values. [W]
        """

        # Validate `time`
        time = self._validate_time(time)
        n_time = len(time)

        # Retrieve instance attributes
        load = self.load
        model = self.model

        # Number of elements in `load`
        n_elements = len(load)

        # Preallocate curve (with length of `time` input)
        curve = np.array([0] * n_time)

        # For each element
        for e in range(n_elements):

            # Current PowerData
            current_powerdata = load[e]

            # Current model
            current_model = model[e]

            # Compute current curve
            current_curve = self._single_curve(current_powerdata, current_model, time)

            # Add current curve to total curve
            current_curve = np.array(current_curve)
            curve = curve + current_curve

        # Output curve converted into list
        curve = curve.tolist()
        return curve

    # ------------------------------------------------------------------
    # VISUALIZATION
    # ------------------------------------------------------------------

    @classmethod
    def _validate_n_points(cls, n_points):
        """
        Validate 'n_points' input. If `None`, retrieves default; else
        must be non-negative integer.
        """
        if not n_points:
            n_points = cls._n_points
        else:
            n_points = int(n_points)
            if n_points < 0:
                cls._issue_error("n_points")
        return n_points

    @staticmethod
    def _refine_vector(vector, n_points):
        """
        Add `n_point` equidistant points between each pair of points in
        the input `vector`.
        """

        # Number of vector segments
        n_segments = len(vector) - 1

        # Preallocate output
        refined_vector = []

        # Validate `n_points`
        n = n_points
        if n == 0:
            refined_vector = vector  # No alterations to vector
        else:

            # For each curve segment (i.e. pair of points)
            for s in range(n_segments):
                first = vector[s]
                last = vector[s + 1]
                refined_segment = np.linspace(first, last, n + 1, endpoint=False)
                refined_segment = refined_segment.tolist()
                refined_vector = refined_vector + refined_segment
            refined_vector.append(vector[-1])

        # Output refined vector
        return refined_vector

    def plot(self, ax=None, n_points=None, detailed=False, **kwargs):
        """
        Plot a `PowerLoad` curve, built using the attributes that define
        the instance. The number of points interpolated in each curve
        segment can be specified.

        This method applies the `matplotlib.pyplot.plot` imported
        method to a list of values built using the `curve` method.
        The default options for this plot are defined as class
        attributes, but can be overridden.

        This method can also plot the individual `PowerData` objects
        stored in the `load` attribute that define the `PowerLoad`
        instance.

        Parameters
        ----------
        n_points: `int`
            Number of points interpolated in each curve segment. The
            default value is `None`, which indicates to the method
            that the default value should be used, defined as a class
            attribute.
        detailed: `bool`
            Determines whether the plot will include all individual
            `PowerData` instances (computed with their respective
            `model` entries), that summed result in the normal plotted
            curve. By default this input is set to `False`.
        **kwargs = `dict`
            Options for the `plot` method.

        Returns
        -------
        plot_list: `list`
            List of plot objects created by the `matplotlib` package.
            The first element of the list is the plot object created
            using the `pyplot.plot`, while the second element of the
            list is the plot object created using the `pyplot.text`
            method.
            If the `detailed` argument is set to `True`, the list
            continues to include the lists of plot objects created by
            the `PowerData` class, with the addition of plotted curves
            for the visualization of the model selected for each load.
        """

        # Validate axes
        ax = imported_utilities.validate_axes(ax)

        # Retrieve default plot options (main curve)
        default = self._plot_defaults

        # Set each default options in kwargs, if not specified
        kwargs = imported_utilities.add_dict_entries(kwargs, default)

        # Validate `n_points`
        n_points = self._validate_n_points(n_points)

        # Retrieve instance attributes
        name = self.name
        load = self.load
        model = self.model

        # Number of elements in `load`
        n_elements = len(load)

        # Preallocate time vector for plotting
        time = []

        # For each element
        for e in range(n_elements):

            # Current PowerData time vector
            current_powerdata = load[e]
            current_time = current_powerdata.time

            # Refine current time vector
            current_time = self._refine_vector(current_time, n_points)

            # Append current time in time vector for plotting
            time = time + current_time

        # Sort and unique of comeplete time vector
        time = list(set(time))
        time.sort()

        # Compute complete curve
        curve = self.curve(time)

        # Preallocate output
        plot_list = []

        # Plot curve as line
        label = name + " (curve)"
        plot_obj = ax.plot(time, curve, label=label, **kwargs)
        plot_list.append(plot_obj)

        # Add descriptive label to curve
        index = self._ind_point
        text = f"{name} (PowerLoad)"
        label = name + " (name)"
        angle = self._text_angle
        plot_obj = ax.text(time[index], curve[index], text, label=label, rotation=angle)
        plot_list.append(plot_obj)

        # Validate `detailed` option
        if detailed:

            # Retrieve default plot options (detailed curves)
            default = self._detailed_defaults

            # Modify plot options for detailed curves
            kwargs.update(default)

            # For each element
            for e in range(n_elements):

                # Current PowerData
                current_powerdata = load[e]

                # Current model
                current_model = model[e]

                # Compute current curve
                current_curve = self._single_curve(
                    current_powerdata, current_model, time
                )

                # Plot PowerData with same plot options
                current_plot_list = current_powerdata.plot(**kwargs)

                # Plot current curve as line with descriptive label
                plot_obj = ax.plot(time, current_curve, **kwargs)

                # Append current plot list with current curve
                current_plot_list.append(plot_obj)

                # Store current plot list in output
                plot_list.append(current_plot_list)

            # Return plot object
            return plot_list


# ######################################################################
# PHASE LOAD
# ######################################################################


class PhaseLoad(imported_abc):
    """
    Representation of the total power load during a pulse phase.

    Defines the phase load with a set of `PowerLoad` instances.

    Parameters
    ----------
    name: 'str'
        Description of the `PhaseLoad` instance.
    phase: `PowerCyclePhase`
        Pulse phase specification, that determines in which phase the
        load happens.
    load_set: `PowerLoad` | `list`[`PowerLoad`]
        Collection of instances of the `PowerLoad` class that define
        the `PhaseLoad` object.
    """

    # ------------------------------------------------------------------
    # CLASS ATTRIBUTES
    # ------------------------------------------------------------------

    # Error messages
    _errors = {}

    # ------------------------------------------------------------------
    # CONSTRUCTOR
    # ------------------------------------------------------------------
    def __init__(self, name, phase, load_set):

        # Call superclass constructor
        super().__init__(name)

        # Validate `phase`
        self.phase = self._validate_phase(phase)

        # Validate `load_set`
        self.load_set = self._validate_load_set(load_set)

        # Validate created instance
        self._sanity()

    @classmethod
    def _validate_phase(cls, phase):
        """
        Validate 'phase' input to be a valid PowerCycleTimeline phase.
        """

        return phase

    @classmethod
    def _validate_load_set(cls, load_set):
        """
        Validate 'load_set' input to be a list of `PowerLoad` instances.
        """
        load_set = super()._validate_list(load_set)
        for element in load_set:
            PowerLoad._validate(element)
        return load_set

    # ------------------------------------------------------------------
    # OPERATIONS
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # VISUALIZATION
    # ------------------------------------------------------------------


# ######################################################################
# PULSE LOAD
# ######################################################################
class PulseLoad:
    """
    Representation of the total power load during a complete pulse.

    Defines the pulse load with a set of `PhaseLoad` instances.

    Parameters
    ----------
    name: 'str'
        Description of the `PhaseLoad` instance.
    pulse: `PowerCyclePulse`
        Pulse specification, that determines in which order the pulse
        phases happen.
    """

    pass
