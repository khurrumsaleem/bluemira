"""
Base classes for the power cycle model.
"""

# Import
# import numpy as np
import matplotlib.pyplot as plt

from bluemira.power_cycle.utilities import PowerCycleUtilities as imported_utilities

# from scipy.interpolate import interp1d as imported_interp1d

# #################################################################### #
# POWER DATA
# #################################################################### #


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
    data: `float`
        List of power values that define the PowerData [W]
    time: `float`
        List of time values that define the PowerData [s]
    """

    # ---------------------------------------------------------------- #
    # CLASS ATTRIBUTES
    # ---------------------------------------------------------------- #

    # Plot defaults (arguments for `matplotlib.pyplot.scatter`)
    plot_defaults = {
        "c": "k",  # Marker color
        "s": 100,  # Marker size
        "marker": "*",  # Marker style
    }

    # ---------------------------------------------------------------- #
    # CONSTRUCTOR
    # ---------------------------------------------------------------- #
    def __init__(self, time, data):

        # Validate inputs
        self.data = self.__validate_input(data)
        self.time = self.__validate_input(time)

        # Verify time is an increasing vector
        self.__is_increasing(self.time)

        # Validate created instance
        self.__sanity()

    @classmethod
    def __validate_input(self, input):
        """
        Validate an input for class instance creation to be a list of
        floats.
        """
        for i in input:
            if not isinstance(i, (int, float)):
                print(
                    f"""
                    The inputs used to create an instance of the
                    {self.__class__.__name__} class must be lists of
                    floats.
                    """
                )
                raise TypeError()
        return input

    @classmethod
    def __is_increasing(self, input):
        """
        Validate an input for class instance creation to be an
        increasing list.
        """
        check_increasing = []
        for i in range(len(input) - 1):
            check_increasing.append(input[i] <= input[i + 1])

        if not all(check_increasing):
            print(
                f"""
                    The `time` input used to create an instance of the
                    {self.__class__.__name__} class must be an
                    increasing list.
                    """
            )
            raise ValueError()
        return input

    def __sanity(self):
        """
        Validate that `data` and `time` attributes both have the same
        length, so that they univocally represent power values in time.
        """
        length_data = len(self.data)
        length_time = len(self.time)
        if length_data != length_time:
            print(
                f"""
                The attributes `data` and `time` of an instance of the
                {self.__class__.__name__} class must have the same
                length.
                """
            )
            raise ValueError()

    # ---------------------------------------------------------------- #
    # OPERATIONS
    # ---------------------------------------------------------------- #
    @classmethod
    def _validate_PowerData(self, object):
        """
        Validate `object` to be an instance of the this class.
        """
        if not isinstance(object, PowerData):
            print(
                f"""
                The tested object is not an instance of the
                {self.__class__.__name__} class.
                """
            )
            raise TypeError()
        return object

    # ---------------------------------------------------------------- #
    # VISUALIZATION
    # ---------------------------------------------------------------- #
    def plot(self, **kwargs):

        # Retrieve default plot options
        default = self.plot_defaults

        # Set each default options in kwargs, if not specified
        kwargs = imported_utilities.add_dict_entries(kwargs, default)

        # Retrieve instance characteristics
        time = self.time
        data = self.data

        # Plot
        plt.scatter(time, data, **kwargs)
        plt.show()


# #################################################################### #
# GENERIC POWER LOAD
# #################################################################### #


'''
class PowerLoad:
    """
    Generic representation of a power load curve.

    Defines a power load curve with a set of `data` and `time` vectors
    and a `model` specification to compute additional values between
    data points.

    Parameters
    ----------
    model: `str`
        Type of model to apply to `data` and `time` to generate curve
    data: `float`
        List of power values that define curve [W]
    time: `float`
        List of time values that define curve [s]

    Attributes
    ----------
    curve: `PowerCurve`
        Original `data` and `time` data used to define instance.
    """

    # ---------------------------------------------------------------- #
    # CLASS ATTRIBUTES
    # ---------------------------------------------------------------- #

    # Plot defaults (arguments for `matplotlib.pyplot.plot`)
    plot_defaults = {
        "c": "k",           # Line color
        "lw": 2,            # Line width
        "ls": "-",          # Line style
    }
    n_points = 100          # number of points in each curve segment

    # Implemented models (add model name here after implementation)
    valid_models = ["ramp", "step"]

    # ---------------------------------------------------------------- #
    # CONSTRUCTOR
    # ---------------------------------------------------------------- #
    def __init__(self, model, data, time):

        # Validate & store model
        self.model = self.__validate_model(model)

        # Create & store PowerCurve with original input data
        self.curve = PowerData(data, time)

    @classmethod
    def __validate_model(cls, model):
        """
        Validate 'model' input.
        """
        valid_models = cls.valid_models
        msg_models = ", ".join(valid_models)
        if model not in valid_models:
            print(
                f"""
                The argument given for the attribute `model` is not a
                valid value. Only the following models are currently
                implemented in class {cls.__class__.__name__}:
                {msg_models}.
                """
            )
            raise ValueError()

        return model

    @classmethod
    def _error(cls, type):

        # ---------------------------------------------------------------- #
        # OPERATIONS
        # ---------------------------------------------------------------- #

    def load(self, time):
        """
        Calculate power load values at the specified times, based on
        the defined `curve` and `model`.

        Parameters
        ----------
        time: `float`
            List of time values [s]

        Returns
        -------
        data: `float`
            List of power values [W]

        """

        # Retrieve PowerLoad `data`, `time` and `model`
        data = self.curve.data
        time = self.curve.time
        model = self.model

        # Validate `model`
        if model == 'ramp':

        elif model == 'step':

        else:

    '''

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
