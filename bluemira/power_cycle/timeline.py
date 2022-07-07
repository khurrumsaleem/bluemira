"""
Classes to define the timeline for Power Cycle simulations.
"""

# Import
from typing import Union  # , List

from bluemira.power_cycle.base import PowerCycleABC as imported_abc
from bluemira.power_cycle.base import PowerCycleError as imported_error

# from bluemira.power_cycle.base import PowerCycleUtilities as imported_utilities

# ######################################################################
# POWER CYCLE PHASE
# ######################################################################


class PowerCyclePhase(imported_abc):
    """
    Class to define phases for a Power Cycle pulse.

    Parameters
    ----------
    name: 'str'
        Description of the `PowerCyclePhase` instance.
    label: `str`
        Shorthand label for addressing the `PowerCyclePhase` instance.
    dependency: `str`
        Classification of the `PowerCyclePhase` instance in terms of
        time-dependent calculation: 'ss' (stready-state) or 'tt'
        (transient).
    duration: `float`
        Phase duration
    """

    # ------------------------------------------------------------------
    # CLASS ATTRIBUTES
    # ------------------------------------------------------------------

    _valid_dependencies = {
        "ss": "steady-state",
        "tt": "transient",
    }

    # Error messages
    _errors = {
        "label": imported_error(
            "Value",
            """
                The argument given for the attribute `label` is not a
                valid value. Instances of the class %CLASS_NAME must be
                labeled with strings of 3 characters.
                """,
        ),
        "dependency": imported_error(
            "Value",
            """
                The argument given for the attribute `dependency` is not
                a valid value. Only the following values are accepted:
                %_VALID_DEPENDENCIES.
                """,
        ),
    }

    # ------------------------------------------------------------------
    # CONSTRUCTOR
    # ------------------------------------------------------------------
    def __init__(self, name, label: str, dependency: str, duration: Union[int, float]):

        # Call superclass constructor
        super().__init__(name)

        # Validate label
        self.label = self._validate_label(label)

        # Validate dependency
        self.dependency = self._validate_dependency(dependency)

    @classmethod
    def _validate_label(cls, label):
        """
        Validate `label` input for class instance creation to be a
        string of length 3.
        """
        if not len(label) == 3:
            cls._issue_error("label")
        return input

    @classmethod
    def _validate_dependency(cls, dependency):
        """
        Validate `dependency` input for class instance creation to be
        one of the valid values.
        """
        valid_dependencies = cls._valid_dependencies.keys()
        if dependency not in valid_dependencies:
            cls._issue_error("dependency")
        return input

    # ------------------------------------------------------------------
    # OPERATIONS
    # ------------------------------------------------------------------


# ######################################################################
# POWER CYCLE PULSE
# ######################################################################


class PowerCyclePulse(imported_abc):
    """
    Class to define pulses for a Power Cycle timeline.
    """

    pass


# ######################################################################
# POWER CYCLE TIMELINE
# ######################################################################
class PowerCycleTimeline(imported_abc):
    """
    Class to define a timeline for Power Cycle simulations.

    Parameters
    ----------
    name: 'str'
        Description of the `PowerCycleTimeline` instance.
    pulse_set: `list`[`PowerCyclePulse`]

    """

    # ------------------------------------------------------------------
    # CLASS ATTRIBUTES
    # ------------------------------------------------------------------

    _valid_phases = []

    # ------------------------------------------------------------------
    # CONSTRUCTOR
    # ------------------------------------------------------------------
    def __init__(self, name, pulse_set):

        # Call superclass constructor
        super().__init__(name)

        # Validate set of pulses
        self.pulse_set = self._validate_pulse_set(pulse_set)

    @classmethod
    def _validate_pulse_set(cls, pulse_set):
        """
        Validate `pulse_set` input to be a list of instances of the
        `PowerCyclePulse` class.
        """
        return pulse_set

    # ------------------------------------------------------------------
    # OPERATIONS
    # ------------------------------------------------------------------
