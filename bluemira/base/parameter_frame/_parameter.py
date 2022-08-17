import copy
from dataclasses import dataclass
from typing import Dict, Generic, List, Tuple, Type, TypedDict, TypeVar

from typeguard import typechecked

_ParamValueT = TypeVar("_ParamValueT")


@dataclass
class ParameterValue(Generic[_ParamValueT]):
    """Holds parameter value information."""

    value: _ParamValueT
    source: str


class NewParameter(Generic[_ParamValueT]):
    """
    Represents a parameter with physical units.

    Parameters
    ----------
    name: str
        The name of the parameter.
    value: _ParamValueT
        The parameter's value.
    unit: str
        The parameter's unit.
    source: str
        The origin of the parameter's value.
    description: str
        A description of the parameter.
    long_name: str
        A longer name for the parameter.
    _value_types: Tuple[Type, ...]
        Allowed types for `value`. An error is raised if `value` is not
        one of these types. Optional argument, no type checking is
        performed on `value` if this is not given.
    """

    @typechecked
    def __init__(
        self,
        name: str,
        value: _ParamValueT,
        unit: str = "",
        source: str = "",
        description: str = "",
        long_name: str = "",
        _value_types: Tuple[Type, ...] = None,
    ):
        if _value_types:
            if float in _value_types and isinstance(value, int):
                value = float(value)
            elif not isinstance(value, _value_types):
                raise TypeError(
                    f'type of argument "value" must be one of {_value_types}; '
                    f"got {type(value)} instead."
                )
        self._name = name
        self._value = value
        self._unit = unit
        self._source = source
        self._description = description
        self._long_name = long_name

        self._history: List[ParameterValue] = []
        self._add_history_record()

    def __repr__(self) -> str:
        """String repr of class instance."""
        return f"<NewParameter({self.name}={self.value}{self.unit})>"

    def history(self) -> List[ParameterValue]:
        """Return the history of this parameter's value."""
        return copy.deepcopy(self._history)

    @typechecked
    def set_value(self, new_value: _ParamValueT, source: str = ""):
        """Set the parameter's value and update the source."""
        self._value = new_value
        self._source = source
        self._add_history_record()

    def to_dict(self) -> Dict:
        """Serialize the parameter to a dictionary."""
        out = {"name": self.name, "value": self.value}
        for field in ["unit", "source", "description", "long_name"]:
            if value := getattr(self, field):
                out[field] = value
        return out

    @property
    def name(self) -> str:
        """Return the name of the parameter."""
        return self._name

    @property
    def value(self) -> _ParamValueT:
        """Return the current value of the parameter."""
        return self._value

    @value.setter
    def value(self, new_value: _ParamValueT):
        self.set_value(new_value, source="")

    @property
    def unit(self) -> str:
        """Return the physical unit of the parameter."""
        return self._unit

    @property
    def source(self) -> str:
        """Return the source that last set the value of this parameter."""
        return self._source

    @property
    def long_name(self) -> str:
        """Return a long name for this parameter."""
        return self._long_name

    @property
    def description(self) -> str:
        """Return a description for the parameter."""
        return self._description

    def _add_history_record(self):
        history_entry = ParameterValue(self.value, self.source)
        self._history.append(history_entry)


class ParamDictT(TypedDict, Generic[_ParamValueT], total=False):
    """
    Gives the structure of a Dict that can be converted to a Parameter.

    This is purely used for typing.
    """

    name: str
    value: _ParamValueT
    unit: str
    source: str
    description: str
    long_name: str
