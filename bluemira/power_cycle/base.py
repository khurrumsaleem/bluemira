"""
Base classes for the power cycle model.
"""

import matplotlib.pyplot as plt

# Import
import numpy as np
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
    time: `float`
        List of time values that define the PowerData. [s]
    data: `float`
        List of power values that define the PowerData. [W]
    """

    # ------------------------------------------------------------------
    # CLASS ATTRIBUTES
    # ------------------------------------------------------------------

    # Plot defaults (arguments for `matplotlib.pyplot.scatter`)
    plot_defaults = {
        "c": "k",  # Marker color
        "s": 100,  # Marker size
        "marker": "x",  # Marker style
    }

    # ------------------------------------------------------------------
    # CONSTRUCTOR
    # ------------------------------------------------------------------
    def __init__(self, time, data):

        # Validate inputs
        self.data = self.__validate_input(data)
        self.time = self.__validate_input(time)

        # Verify time is an increasing vector
        self.__is_increasing(self.time)

        # Validate created instance
        self.__sanity()

    @classmethod
    def __validate_input(cls, input):
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
    def __is_increasing(cls, input):
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

    def __sanity(self):
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
    def plot(self, **kwargs):
        """
        Plot the points that define the `PowerData` instance.

        This method applies the `matplotlib.pyplot.scatter` imported
        method to the vectors that define the `PowerData` instance. The
        default options for this plot are defined as class attributes,
        but can be overridden.

        Parameters
        ----------
        **kwargs = `dict``
            Options for the `scatter` method.
        """

        # Retrieve default plot options
        default = self.plot_defaults

        # Set each default options in kwargs, if not specified
        kwargs = imported_utilities.add_dict_entries(kwargs, default)

        # Retrieve instance characteristics
        time = self.time
        data = self.data

        # Plot
        plt.scatter(time, data, **kwargs)


# ######################################################################
# GENERIC POWER LOAD
# ######################################################################
class PowerLoad:
    """
    Generic representation of a power load curve.

    Defines a power load curve with a set of `data` and `time` vectors
    and a `model` specification to compute additional values between
    data points.

    Parameters
    ----------
    time: `float`
        List of time values that define curve. [s]
    data: `float`
        List of power values that define curve. [W]
    model: `str`
        Type of model that defines values between `load` points. By
        default, a 'ramp' model is applied. Valid models include:
        - 'ramp'
        - 'step'

    Attributes
    ----------
    load: `PowerData`
        Original `time` and `data` data used to define instance.
    """

    # ------------------------------------------------------------------
    # CLASS ATTRIBUTES
    # ------------------------------------------------------------------

    # Plot defaults (arguments for `matplotlib.pyplot.plot`)
    plot_defaults = {
        "c": "k",  # Line color
        "lw": 2,  # Line width
        "ls": "-",  # Line style
    }
    n_points = 100  # number of points in each curve segment

    # Implemented models (add model name here after implementation)
    valid_models = ["ramp", "step"]

    # ------------------------------------------------------------------
    # CONSTRUCTOR
    # ------------------------------------------------------------------
    def __init__(self, time, data, model="ramp"):

        # Validate & store model
        self.model = self.__validate_model(model)

        # Create & store PowerCurve with original input data
        self.load = PowerData(time, data)

    @classmethod
    def __validate_model(cls, model):
        """
        Validate 'model' input.
        """
        valid_models = cls.valid_models
        if model not in valid_models:
            cls._issue_error("model")
        return model

    @classmethod
    def _issue_error(cls, type):

        # Class name
        class_name = cls.__class__.__name__

        # Validate error `type`
        if type == "model":
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

    def curve(self, time):
        """
        Create a curve by calculating power load values at the specified
        times.

        This method applies the `scipy.interpolate.interp1d` imported
        method to the vectors defined by the `load` attribute. The kind
        of interpolation is determined by the `model` attribute. Any
        out-of-bound values are set to zero.

        Parameters
        ----------
        time: `float`
            List of time values [s]

        Returns
        -------
        data: `float`
            List of power values [W]
        """

        # Validate `model`
        model = self.model
        if model == "ramp":
            k = "linear"  # Linear interpolation
        elif model == "step":
            k = "previous"  # Previous-value interpolation
        else:
            self._issue_error("model")

        # Define interpolation function
        x = self.load.time
        y = self.load.data
        b = False  # out-of-bound values do not raise error
        f = (0, 0)  # below-bounds/above-bounds values set to 0
        lookup = imported_interp1d(x, y, kind=k, fill_value=f, bounds_error=b)

        # Output interpolated curve
        curve = list(lookup(time))
        return curve

    # ------------------------------------------------------------------
    # VISUALIZATION
    # ------------------------------------------------------------------
    @classmethod
    def __validate_n_points(cls, n_points):
        """
        Validate 'n_points' input. If `None`, retrieves default; else
        must be non-negative integer.
        """
        if not n_points:
            n_points = cls.n_points
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

    def plot(self, n_points=None, **kwargs):
        """
        Plot a `PowerLoad` curve, built using the attributes that define
        the instance. The number of points interpolated in each curve
        segment can be specified.

        This method applies the `matplotlib.pyplot.plot` imported
        method to the `load` attribute of the `PowerLoad` instance.
        The default options for this plot are defined as class
        attributes, but can be overridden.

        Parameters
        ----------
        n_points: `int`
            Number of points interpolated in each curve segment. The
            default value is `None`, which indicates to the method
            that the default value should be used, defined as a class
            attribute.
        **kwargs = `dict``
            Options for the `scatter` method.
        """

        # Retrieve default plot options
        default = self.plot_defaults

        # Set each default options in kwargs, if not specified
        kwargs = imported_utilities.add_dict_entries(kwargs, default)

        # Validate `n_points`
        n_points = self.__validate_n_points(n_points)

        # Retrieve and refine `time`
        time = self.load.time
        time = self._refine_vector(time, n_points)

        # Compute curve
        curve = self.curve(time)

        # Plot curve as a line
        plt.plot(time, curve, **kwargs)

        # Erase unnecessary plot options for PowerData

        # Plot load with same plot options
        self.load.plot(**kwargs)


'''
    @staticmethod
    def interpolate_load(old_PowerCurve, new_time):
        """
        Applies the `interpolate` method of the package `scipy` to
        derive a new load vector for a desired time vector, based on an
        instance of the PowerCurve class for the interpolation.

        Parameters
        ----------
        old_PowerCurve: instance of the PowerCurve class
        new_time: float

        Returns
        -------
        new_load: float
        """

        # Create general interpolating function
        x = old_PowerCurve.time
        y = old_PowerCurve.load
        k = 'linear'
        f = float("nan")
        old_lookup = imported_interp1d(x, y, kind=k, fill_value=f)

        # First and last elements in `old_PowerCurve` time
        old_first = x[0]
        old_last = x[-1]

        # First and last elements in x
        # x_first = x[0]
        # x_last = x[-1]

        # Preallocate `new_load`
        n_new = len(new_time)
        new_load = [0] * n_new

        # Look-up values for `new_time` if necessary
        index_range = range(n_new)
        for i in index_range:

            # Current time
            t = new_time[i]

            # Check if t is out-of-bounds of `old_time`
            t_below_first = t < old_first
            t_above_last = t > old_last
            t_outbound = t_below_first or t_above_last

            # Only interpolate if t is in-bounds
            if not t_outbound:
                load_value = old_lookup(t)
                new_load[i] = load_value.tolist()

        return new_load
'''
