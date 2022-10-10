from __future__ import annotations

import copy
import json
from contextlib import suppress
from dataclasses import dataclass, fields
from typing import (
    Any,
    Dict,
    Generator,
    Iterable,
    List,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
    get_args,
)

import pint
from tabulate import tabulate

from bluemira.base.constants import (
    ANGLE_UNITS,
    base_unit_defaults,
    combined_unit_defaults,
    combined_unit_dimensions,
    raw_uc,
)
from bluemira.base.parameter_frame._parameter import (
    ParamDictT,
    Parameter,
    ParameterValueType,
)

_PfT = TypeVar("_PfT", bound="ParameterFrame")


@dataclass
class ParameterFrame:
    """
    A data class to hold a collection of `Parameter` objects.

    The class should be declared using on of the following forms:

    .. code-block:: python

        @parameter_frame
        class MyFrame:
            param_1: Parameter[float]
            param_2: Parameter[int]


        @dataclass
        class AnotherFrame(ParameterFrame):
            param_1: Parameter[float]
            param_2: Parameter[int]

    """

    def __iter__(self) -> Generator[Parameter, None, None]:
        """
        Iterate over this frame's parameters.

        The order is based on the order in which the parameters were
        declared.
        """
        for field in fields(self):
            yield getattr(self, field.name)

    def update_values(self, new_values: Dict[str, ParameterValueType], source: str = ""):
        """Update the given parameter values."""
        for key, value in new_values.items():
            param: Parameter = getattr(self, key)
            param.set_value(value, source)

    @classmethod
    def from_dict(
        cls: Type[_PfT],
        data: Dict[str, ParamDictT],
        allow_unknown=False,
    ) -> _PfT:
        """Initialize an instance from a dictionary."""
        data = copy.deepcopy(data)
        kwargs: Dict[str, Parameter] = {}
        for member in cls.__dataclass_fields__:
            try:
                param_data = data.pop(member)
            except KeyError as e:
                raise ValueError(f"Data for parameter '{member}' not found.") from e

            value_type = _validate_parameter_field(
                member, cls.__dataclass_fields__[member].type
            )
            try:
                _validate_units(param_data, value_type)
            except pint.errors.PintError as pe:
                raise ValueError("Unit conversion failed") from pe

            kwargs[member] = Parameter(
                name=member, **param_data, _value_types=value_type
            )

        if not allow_unknown and len(data) > 0:
            raise ValueError(f"Unknown parameter(s) {str(list(data))[1:-1]} in dict.")
        return cls(**kwargs)

    @classmethod
    def from_frame(cls: Type[_PfT], frame: ParameterFrame) -> _PfT:
        """Initialise an instance from another ParameterFrame."""
        kwargs = {}
        for field in cls.__dataclass_fields__:
            try:
                kwargs[field] = getattr(frame, field)
            except AttributeError as attr_error:
                raise ValueError(
                    f"Cannot create '{cls.__name__}' from '{type(frame).__name__}'. "
                    f"{type(frame).__name__} does not contain field '{field}'."
                ) from attr_error
        return cls(**kwargs)

    @classmethod
    def from_json(cls: Type[_PfT], json_in: Union[str, json.SupportsRead]) -> _PfT:
        """Initialise an instance from a JSON file, string, or reader."""
        if hasattr(json_in, "read"):
            # load from file stream
            return cls.from_dict(json.load(json_in))
        elif not isinstance(json_in, str):
            raise ValueError(f"Cannot read JSON from type '{type(json_in).__name__}'.")
        elif not json_in.startswith("{"):
            # load from file
            with open(json_in, "r") as f:
                return cls.from_dict(json.load(f))
        # load from a JSON string
        return cls.from_dict(json.loads(json_in))

    def to_dict(self) -> Dict[str, Dict[str, Any]]:
        """Serialize this ParameterFrame to a dictionary."""
        out = {}
        for param_name in self.__dataclass_fields__:
            param_data = getattr(self, param_name).to_dict()
            # We already have the name of the param, and use it as a
            # key. No need to repeat the name in the data, so pop it.
            param_data.pop("name")
            out[param_name] = param_data
        return out

    def tabulate(self, keys: Optional[List] = None, tablefmt: str = "fancy_grid") -> str:
        """
        Tabulate the ParameterFrame

        Parameters
        ----------
        keys: Optional[List]
            table column keys
        tablefmt: str (default="fancy_grid")
            The format of the table - see
            https://github.com/astanin/python-tabulate#table-format

        Returns
        -------
        tabulated: str
            The tabulated DataFrame
        """
        columns = list(ParamDictT.__annotations__.keys()) if keys is None else keys
        rec_col = copy.deepcopy(columns)
        rec_col.pop(columns.index("name"))
        records = sorted(
            [
                [key, *[param.get(col, "N/A") for col in rec_col]]
                for key, param in self.to_dict().items()
            ]
        )
        return tabulate(
            records,
            headers=columns,
            tablefmt=tablefmt,
            showindex=False,
            numalign="right",
        )

    def __str__(self) -> str:
        """
        Pretty print ParameterFrame
        """
        return self.tabulate()


def _validate_parameter_field(field, member_type: Type) -> Tuple[Type, ...]:
    if (member_type is not Parameter) and (
        not hasattr(member_type, "__origin__") or member_type.__origin__ is not Parameter
    ):
        raise TypeError(f"Field '{field}' does not have type Parameter.")
    value_types = get_args(member_type)
    return value_types


def _validate_units(param_data: Dict, value_type: Iterable[Type]):

    try:
        quantity = pint.Quantity(param_data["value"], param_data["unit"])
    except KeyError as ke:
        raise ValueError("Parameters need a value and a unit") from ke
    except TypeError as te:
        if not isinstance(param_data["value"], bool):
            raise te
        param_data["unit"] = "dimensionless"
        return

    if dimensionality := quantity.units.dimensionality:
        unit = _fix_combined_units(_remake_units(dimensionality))
    else:
        unit = quantity.units

    unit = _fix_weird_units(unit, quantity.units)

    if unit != quantity.units:
        val = raw_uc(quantity.magnitude, quantity.units, unit)
        if isinstance(param_data["value"], int) and int in value_type:
            val = int(val)
        param_data["value"] = val

    param_data["unit"] = f"{unit:~P}"


def _remake_units(dimensionality: Union[Dict, pint.unit.UnitsContainer]) -> pint.Unit:
    """Reconstruct unit from its dimensionality"""
    dim_list = list(map(base_unit_defaults.get, dimensionality.keys()))
    dim_pow = list(dimensionality.values())
    return pint.Unit(".".join([f"{j[0]}^{j[1]}" for j in zip(dim_list, dim_pow)]))


def _fix_combined_units(unit: pint.Unit) -> pint.Unit:
    """Converts base unit to a composite unit if they exist in the defaults"""
    dim_keys = list(combined_unit_dimensions.keys())
    dim_val = list(combined_unit_dimensions.values())
    with suppress(ValueError):
        return pint.Unit(
            combined_unit_defaults[dim_keys[dim_val.index(unit.dimensionality)]]
        )
    return pint.Unit(unit)


def _convert_angle_units(
    modified_unit: pint.Unit, orig_unit_str: str, angle_unit: str
) -> pint.Unit:
    """
    Converts angle units to the base unit default for angles.

    Angles are dimensionless therefore dimensionality conversion
    from pint doesn't work. Conversions between angle units is also not
    very robust.

    Parameters
    ----------
    modified_unit: pint.Unit
        reconstructed unit without the angle
    orig_unit_str: str
        the user supplied unit (without spaces)
    angle_unit: str
        the angle unit in `orig_unit`

    Returns
    -------
    pint.Unit;
        the new unit

    """
    breaking_units = ["steradian", "square_degree"]
    new_angle_unit = base_unit_defaults["[angle]"]
    for b in breaking_units:
        if b in orig_unit_str:
            raise NotImplementedError(f"{breaking_units} not supported for conversion")
    if f"{angle_unit}**" in orig_unit_str:
        raise NotImplementedError("Exponent angles >1, <-1 are not supported")
    unit_list = orig_unit_str.split("/", 1)
    exp = "." if angle_unit in unit_list[0] else "/"
    modified_unit = "".join(str(modified_unit).split(angle_unit))
    return pint.Unit(f"{modified_unit}{exp}{new_angle_unit}")


def _fix_weird_units(modified_unit: pint.Unit, orig_unit: pint.Unit) -> pint.Unit:
    """
    Essentially a crude unit parser for when we have no dimensions
    or non-commutative dimensions.

    Full power years (dimension [time]) and displacements per atom (dimensionless)
    need to be readded to units as they will be removed by the dimensionality conversion.

    Angle units are dimensionless and conversions between them are not robust

    """
    unit_str = f"{orig_unit:C}"

    ang_unit = [ang for ang in ANGLE_UNITS if ang in unit_str]
    if len(ang_unit) > 1:
        raise ValueError(f"More than one angle unit not supported...🤯 {orig_unit}")
    elif len(ang_unit) == 1:
        ang_unit = ang_unit[0]
    else:
        ang_unit = None

    fpy = "full_power_year" in unit_str
    dpa = "displacements_per_atom" in unit_str

    if not (fpy or dpa) and ang_unit is None:
        return pint.Unit(modified_unit)

    new_unit = _non_comutative_unit_conversion(
        dict(modified_unit.dimensionality), unit_str.split("/")[0], dpa, fpy
    )

    # Deal with angles
    return _convert_angle_units(new_unit, unit_str, ang_unit) if ang_unit else new_unit


def _non_comutative_unit_conversion(dimensionality, numerator, dpa, fpy):
    """
    Full power years (dimension [time]) and displacements per atom (dimensionless)
    need to be readded to units as they will be removed by the dimensionality conversion.

    Full power years even though time based is not the same as straight 'time' and
    is therefore dealt with after other standard unit conversions.

    Only first order of both of these units is dealt with.
    """
    dpa_str = (
        ("dpa." if "displacements_per_atom" in numerator else "dpa^-1.") if dpa else ""
    )
    if fpy:
        if "full_power_year" in numerator:
            dimensionality["[time]"] += -1
            fpy_str = "fpy."
        else:
            dimensionality["[time]"] += 1
            fpy_str = "fpy^-1."

        if dimensionality["[time]"] == 0:
            del dimensionality["[time]"]
    else:
        fpy_str = ""

    return pint.Unit(
        f"{dpa_str}{fpy_str}{_fix_combined_units(_remake_units(dimensionality))}"
    )


def make_parameter_frame(
    params: Union[Dict[str, ParamDictT], ParameterFrame, str, None],
    param_cls: Type[_PfT],
) -> Union[_PfT, None]:
    """
    Factory function to generate a `ParameterFrame` of a specific type.

    Parameters
    ----------
    params: Union[Dict[str, ParamDictT], ParameterFrame, str, None]
        The parameters to initialise the class with.
        This parameter can be several types:

            * Dict[str, ParamDictT]:
                A dict where the keys are parameter names, and the
                values are the data associated with the corresponding
                name.
            * ParameterFrame:
                A reference to the parameters on this frame will be
                assigned to the new ParameterFrame's parameters. Note
                that this makes no copies, so updates to parameters in
                the new frame will propagate to the old, and vice versa.
            * str:
                The path to a JSON file, or, if the string starts with
                '{', a JSON string.
            * None:
                For the case where no parameters are actually required.
                This is intended for internal use, to aid in validation
                of parameters in `Builder`\\s and `Designer`\\s.

    param_cls: Type[ParameterFrame]
        The `ParameterFrame` class to create a new instance of.

    Returns
    -------
    Union[ParameterFrame, None]
        A frame of the type `param_cls`, or `None` if `params` and
        `param_cls` are both `None`.
    """
    if param_cls is None:
        if params is None:
            # Case for where there are no parameters associated with the object
            return params
        raise ValueError("Cannot process parameters, 'param_cls' is None.")
    elif isinstance(params, dict):
        return param_cls.from_dict(params)
    elif isinstance(params, param_cls):
        return params
    elif isinstance(params, str):
        return param_cls.from_json(params)
    elif isinstance(params, ParameterFrame):
        return param_cls.from_frame(params)
    raise TypeError(f"Cannot interpret type '{type(params)}' as {param_cls.__name__}.")
