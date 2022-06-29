"""
Base classes for the power cycle model.
"""
# Import
import numpy as np

# import matplotlib.pyplot as plt
from scipy.interpolate import interp1d as imported_interp1d

from bluemira.power_cycle.utilities import PowerCycleUtilities as imported_utilities

# ######################################################################
# POWER DATA
# ######################################################################


class PowerData:
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
    time: `float`
        List of time values that define the PowerData. [s]
    data: `float`
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

    # ------------------------------------------------------------------
    # CONSTRUCTOR
    # ------------------------------------------------------------------
    def __init__(self, name, time, data):

        # Validate name
        self.name = self._validate_name(name)

        # Validate inputs
        self.data = self._validate_input(data)
        self.time = self._validate_input(time)

        # Verify time is an increasing vector
        self._is_increasing(self.time)

        # Validate created instance
        self._sanity()

    @classmethod
    def _validate_name(cls, name):
        """
        Validate a name for class instance creation to be a string.
        """
        if not isinstance(name, (str)):
            raise TypeError(
                f"""
                The 'name' used to create an instance of the
                {cls.__class__.__name__} class must be a `str`.
                """
            )
        return name

    @classmethod
    def _validate_input(cls, input):
        """
        Validate an input for class instance creation to be a list of
        floats.
        """
        for i in input:
            if not isinstance(i, (int, float)):
                raise TypeError(
                    f"""
                    The inputs used to create an instance of the
                    {cls.__class__.__name__} class must be lists of
                    floats.
                    """
                )
        return input

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
            raise ValueError(
                f"""
                The `time` input used to create an instance of the
                {cls.__class__.__name__} class must be an increasing
                list.
                """
            )
        return input

    def _sanity(self):
        """
        Validate that `data` and `time` attributes both have the same
        length, so that they univocally represent power values in time.
        """
        length_data = len(self.data)
        length_time = len(self.time)
        if length_data != length_time:
            raise ValueError(
                f"""
                The attributes `data` and `time` of an instance of the
                {self.__class__.__name__} class must have the same
                length.
                """
            )

    # ------------------------------------------------------------------
    # OPERATIONS
    # ------------------------------------------------------------------
    @classmethod
    def _validate_PowerData(cls, object):
        """
        Validate `object` to be an instance of the this class.
        """
        if not isinstance(object, PowerData):
            raise TypeError(
                f"""
                The tested object is not an instance of the
                {cls.__class__.__name__} class.
                """
            )
        return object

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

        # Plot
        plot_obj = ax.scatter(time, data, label=name, **kwargs)
        # imported_utilities.apply_plot_options(plot_obj, **kwargs)

        # Add text to plot
        plot_obj = ax.text(time[-1], data[-1], f"{name} (PowerData)")
        # imported_utilities.apply_plot_options(ax, **kwargs)

        # Return plot object
        return plot_obj


# ######################################################################
# GENERIC POWER LOAD
# ######################################################################


class PowerLoad:
    """
    Generic representation of a power load curve.

    Defines a power load curve with a set of `PowerData` instances. Each
    instance must be accompanied by a `model` specification, used to
    compute additional values between data points.

    Parameters
    ----------
    name: 'str'
        Description of the `PowerLoad` instance.
    load: `PowerData` or `list`[`PowerData`]
        Collection of instances of the `PowerData` class that define
        the `PowerLoad` object.
    model: `str` or `list[`str`]
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

    # Implemented models (add model name here after implementation)
    valid_models = ["ramp", "step"]

    # ------------------------------------------------------------------
    # CONSTRUCTOR
    # ------------------------------------------------------------------
    def __init__(self, load, model, name=None):

        # Validate name
        self.name = self._validate_name(name)

        # Validate inputs
        self.load = self._validate_load(load)
        self.model = self._validate_model(model)

        # Validate created instance
        self._sanity()

    @classmethod
    def _validate_name(cls, name):
        """
        Validate 'name' input.
        """
        if not name:
            name = cls.name_default
        elif not isinstance(name, (str)):
            cls._issue_error("name")
        return name

    @classmethod
    def _validate_input(cls, input):
        """
        Validate input to be a list. If just a single value, insert it
        in a list.
        """
        if not isinstance(input, (list)):
            input = [input]
        return input

    @classmethod
    def _validate_load(cls, load):
        """
        Validate 'load' input to be a list of `PowerData` instances.
        """
        load = cls._validate_input(load)
        for element in load:
            PowerData._validate_PowerData(element)
        return load

    @classmethod
    def _validate_model(cls, model):
        """
        Validate 'model' input to be a list of valid models options.
        """
        model = cls._validate_input(model)
        for element in model:
            if element not in cls.valid_models:
                cls._issue_error("model")
        return model

    def _sanity(self):
        """
        Validate instance to have `load` and `model` attributes of
        same length.
        """
        if not len(self.load) == len(self.model):
            raise ValueError(
                f"""
                The attributes `load` and `model` of an instance of the
                {self.__class__.__name__} class must have the same
                length.
                """
            )

    @classmethod
    def _issue_error(cls, type):

        # Class name
        class_name = cls.__class__.__name__

        # Validate error `type`
        if type == "name":
            raise TypeError(
                f"""
                The argument given for the attribute `name` is not a
                valid value for an instance of the class {class_name}.
                Only strings are allowed.
                """
            )
        elif type == "model":
            msg_models = ", ".join(cls.valid_models)
            raise ValueError(
                f"""
                The argument given for the attribute `model` is not a
                valid value. Only the following models are currently
                implemented in class {class_name}: {msg_models}.
                """
            )
        elif type == "n_points":
            raise ValueError(
                f"""
                    The argument given for `n_points` is not a valid
                    value for plotting an instance of the {class_name}
                    class. Only non-negative integers are accepted.
                    """
            )
        else:
            raise ValueError(
                f"""
                Unknown error type for method of class {class_name}.
                """
            )

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
        another = PowerLoad(another_load, another_model, another_name)
        return another

    @classmethod
    def _validate_time(cls, time):
        """
        Validate 'time' input to be a list of numeric values.
        """
        time = cls._validate_input(time)
        for element in time:
            if not isinstance(element, (int, float)):
                raise TypeError(
                    f"""
                    The `time` input used to create a curve with an
                    instance of the {cls.__class__.__name__} class must
                    be numeric or a list of numeric values.
                    """
                )
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

            # No alterations to vector
            refined_vector = vector
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

        # Compute complete curve and plot as line
        curve = self.curve(time)
        plot_obj = ax.plot(time, curve, label=name, **kwargs)

        # Add descriptive label to main curve
        plot_obj = ax.text(time[1], curve[1], f"{name} (PowerLoad)")

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

                # Plot current curve as line with descriptive label
                plot_obj = ax.plot(time, current_curve, **kwargs)
                # imported_utilities.apply_plot_options(plot_obj, **kwargs)

                # Plot PowerData with same plot options
                plot_obj = current_powerdata.plot(**kwargs)
                # imported_utilities.apply_plot_options(plot_obj, **kwargs)

            # Return plot object
            return plot_obj
