"""
Full power cycle model object, used to visualize results
"""
import numpy as np

# class PowerCycleModel:


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
    n_points = 10

    # Implemented models (add model name here after implementation)
    valid_models = ["ramp", "step"]

    # ---------------------------------------------------------------- #
    # -------------------------- CONSTRUCTOR ------------------------- #
    # ---------------------------------------------------------------- #
    def __init__(self, model, load_string, time_string):

        # Validate inputs
        model = self.__validate_input(model)
        load_string = self.__validate_input(load_string)
        time_string = self.__validate_input(time_string)

        # Validate model
        self.model = self.__validate_model(model)

        # Validate vectors
        self.load = self.__validate_vector(load_string)
        self.time = self.__validate_vector(time_string)

        # Validate created instance
        self.__sanity()

    @staticmethod
    def __validate_input(input):
        """
        Validate an input for class instance creation to be a string,
        and remove list-indicator characters
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

    def __sanity(self):
        """
        Validate that 'load' and 'time' attributes both have the same
        length, so that they can be used to generate a curve.
        """
        length_load = len(self.load)
        length_time = len(self.time)
        if length_load != length_time:
            print(
                f"""
            The attributes 'load' and 'time' of an instance of the
            {self.__class__.__name__} class must have the same length.
            """
            )
            raise ValueError()

    # ---------------------------------------------------------------- #
    # ----------------------- CURVE GENERATION ----------------------- #
    # ---------------------------------------------------------------- #
    def generate_curve(self):
        """
        Select which load curve model to apply, and generate power load
        curve.
        """
        load = self.load
        time = self.time
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
        curve = {"power": expanded_load, "times": expanded_time}
        self.curve = curve
        return curve

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
    # ---------------------- CURVE VISUALIZATION --------------------- #
    # ---------------------------------------------------------------- #
    # def plot(self):
