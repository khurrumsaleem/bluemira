"""
Base classes for the power cycle model.
"""
import numpy as np

# #################################################################### #
# ############################ POWER CURVE ########################### #
# #################################################################### #


class PowerCurve:
    """
    Power curve class to store a set of time and load vectors.

    Takes a pair of (time,load) vectors and creates a PowerCurve object
    used to represent the time evolution of a given power in the plant.
    Values between vector points are not defined, since the dependence
    with time is not specified when creating an instance of this class;
    instead, it should be specified by creating instances of this class
    within specialized power load classes such as:
        - `GenericPowerLoad`
        - `CoilPowerLoad`
        - `BOPPowerLoad`

    Parameters
    ----------
    load: float
        List of power values that define curve [W]
    time: float
        List of time values that define curve [s]
    """

    # ---------------------------------------------------------------- #
    # -------------------------- CONSTRUCTOR ------------------------- #
    # ---------------------------------------------------------------- #
    def __init__(self, load, time):

        # Validate inputs
        self.load = self.__validate_input(load)
        self.time = self.__validate_input(time)

        # Verify time is an increasing vector
        self.__is_increasing(self.time)

        # Validate created instance
        self.__sanity()

    @staticmethod
    def __validate_input(input):
        """
        Validate an input for class instance creation to be a list of
        floats.
        """
        for i in input:
            if not isinstance(i, (int, float)):
                print(
                    """
                    The inputs used to create an instance of the
                    'PowerCurve' class must be lists of floats.
                    """
                )
                raise TypeError()
        return input

    @staticmethod
    def __is_increasing(input):
        """
        Validate an input for class instance creation to be an
        increasing list.
        """
        check_increasing = []
        for i in range(len(input) - 1):
            check_increasing.append(input[i] <= input[i + 1])

        if not all(check_increasing):
            print(
                """
                    The 'time' input used to create an instance of the
                    'PowerCurve' class must be an increasing list.
                    """
            )
            raise ValueError()
        return input

    def __sanity(self):
        """
        Validate that 'load' and 'time' attributes both have the same
        length, so that they can be used to generate a PowerCurve.
        """
        length_load = len(self.load)
        length_time = len(self.time)
        if length_load != length_time:
            print(
                f"""
                The attributes 'load' and 'time' of an instance of the
                {self.__class__.__name__} class must have the same
                length.
                """
            )
            raise ValueError()

    # ---------------------------------------------------------------- #
    # -------------------------- OPERATIONS -------------------------- #
    # ---------------------------------------------------------------- #
    @staticmethod
    def _validate_PowerCurve(object):
        """
        Validate 'object' to be an instance of the PowerCurve class.
        """
        if not isinstance(object, PowerCurve):
            print(
                """
                The tested object is not an instance of the PowerCurve
                class.
                """
            )
            raise TypeError()
        return object


# #################################################################### #
# ######################## GENERIC POWER LOAD ######################## #
# #################################################################### #
class GenericPowerLoad:
    """
    Generic power load calculator.

    Takes a 'model' specification and applies to a set of 'load' and
    'time' vectors to generate a power load curve.

    Parameters
    ----------
    model: str
        Type of model to apply to 'load' and 'time' to generate curve
    load: str
        List of power values separated by ',' that define curve [W]
    time: str
        List of time values separated by ',' that define curve [s]
    """

    # Number of points in each curve segment
    n_points = 100

    # Implemented models (add model name here after implementation)
    valid_models = ["ramp", "step"]

    # Default plot characteristics (same as `matplotlib`)
    plot_defaults = {
        "color": "k",  # Marker color
        "s": "100",  # Marker size
    }

    # ---------------------------------------------------------------- #
    # -------------------------- CONSTRUCTOR ------------------------- #
    # ---------------------------------------------------------------- #
    def __init__(self, model, load, time):

        # Validate inputs
        model = self.__validate_input(model)
        load = self.__validate_input(load)
        time = self.__validate_input(time)

        # Validate & store model
        self.model = self.__validate_model(model)

        # Validate vectors
        load = self.__validate_vector(load)
        time = self.__validate_vector(time)

        # Create & store PowerCurve
        self.curve = PowerCurve(load, time)

        # Validate created instance
        self.__sanity()

    @staticmethod
    def __validate_input(input):
        """
        Validate an input for class instance creation to be a string,
        and remove list-indicator characters.
        """
        if isinstance(input, str):
            input = input.replace("[", "")
            input = input.replace("]", "")
            return input
        else:
            print(
                """
                The inputs used to create an instance of the
                'PowerLoad' class must all be strings.
                """
            )
            raise TypeError()

    @staticmethod
    def __validate_model(model):
        """
        Validate 'model' input.
        """
        return model

    @staticmethod
    def __validate_vector(vector):
        """
        Validate vector inputs and convert them to numeric lists.
        """
        # Split string into elements and convert them into floats
        vector = vector.replace(" ", "")
        vector = vector.split(",")
        vector = [float(i) for i in vector]
        return vector

    # ---------------------------------------------------------------- #
    # ----------------------- CURVE GENERATION ----------------------- #
    # ---------------------------------------------------------------- #
    def generate_curve(self):
        """
        Select which load curve model to apply, and generate power load
        curve.
        """
        load = self.curve.load
        time = self.curve.time
        model = self.model
        n_points = self.n_points

        # Select model to be applied
        if model in self.valid_models:
            method_name = "generate_" + model
            generate_segment = getattr(self, method_name)
        else:
            print(
                f"""'
                Unknown 'model' for {self.__class__.__name__} class.
                """
            )
            raise ValueError()

        # Preallocate outputs
        expanded_time = []
        expanded_load = []

        # Number of curve segments
        n_segments = len(self.load) - 1

        # For each curve segment (pair of points)
        for s in range(n_segments):
            first = (time[s], load[s])
            last = (time[s + 1], load[s + 1])
            time_s, load_s = generate_segment(first, last, n_points)
            expanded_time = expanded_time + time_s
            expanded_load = expanded_load + load_s

        # Store & return curve
        curve = PowerCurve(expanded_load, expanded_time)
        # curve = {"power": expanded_load, "times": expanded_time}
        self.curve = curve
        return curve

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
        old_lookup = INTERP1D(x, y, kind=k, fill_value=f)

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

    @staticmethod
    def generate_ramp(first, last, n_points):
        """
        Generate curve segment using 'ramp' model.

        Parameters
        ----------
        first: tuple
            First point in curve segment ([s],[W])
        last: tuple
            Last point in curve segment ([s],[W])
        n_points: int
            Number of points in curve segment
        """
        x1, y1 = first
        x2, y2 = last
        a, b = np.polyfit([x1, x2], [y1, y2], 1)
        expanded_time = np.linspace(x1, x2, n_points).tolist()
        expanded_load = [a * t + b for t in expanded_time]
        return expanded_time, expanded_load

    @staticmethod
    def generate_step(first, last, n_points):
        """
        Generate curve segment using 'ramp' model.

        Parameters
        ----------
        first: tuple
            First point in curve segment ([s],[W])
        last: tuple
            Last point in curve segment ([s],[W])
        n_points: int
            Number of points in curve segment
        """

    # ---------------------------------------------------------------- #
    # ------------------------- VISUALIZATION ------------------------ #
    # ---------------------------------------------------------------- #
    """
    def plot(self, **kwargs):

        # Retrieve default parameters
        default_kwargs = self.plot_defaults
        default_parameters = default_kwargs.keys()
        #n_parameters = len(default_parameters)

        # Preallocate extended kwargs
        extended_kwargs = kwargs

        # For each default parameter
        for parameter in default_parameters:

            # Check if parameter is specified by user
            if parameter not in kwargs:

                # Default value
                value = default_kwargs[parameter]

                # Add parameter to kwargs
                extended_kwargs[parameter] = value

        # Retrieve number of points to plot per curve segment
        n_points = self.n_points

        # Retrieve curve characteristics
        time = self.time
        load = self.load

        # Number of curve points
        n_segments

        plt.scatter(this_time, this_load, color="b", s=m_size)
    """
