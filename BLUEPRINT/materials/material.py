# bluemira is an integrated inter-disciplinary design tool for future fusion
# reactors. It incorporates several modules, some of which rely on other
# codes, to carry out a range of typical conceptual fusion reactor design
# activities.
#
# Copyright (C) 2021 M. Coleman, J. Cook, F. Franza, I.A. Maione, S. McIntosh, J. Morris,
#                    D. Short
#
# bluemira is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# bluemira is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with bluemira; if not, see <https://www.gnu.org/licenses/>.

"""
The home of base material objects. Use classes in here to make new materials.
"""

import json
import numpy as np
import matplotlib.pyplot as plt
import typing
import warnings

import asteval
from CoolProp.CoolProp import PropsSI

with warnings.catch_warnings():
    warnings.simplefilter("ignore", category=UserWarning)
    import neutronics_material_maker as nmm

from BLUEPRINT.base.error import MaterialsError
from bluemira.base.look_and_feel import bluemira_warn
from BLUEPRINT.materials.constants import T_DEFAULT, P_DEFAULT
from BLUEPRINT.utilities.tools import (
    gcm3tokgm3,
    tocelsius,
    tokelvin,
    list_array,
    array_or_num,
)
from bluemira.utilities.tools import is_num

# Set any custom symbols for use in asteval
asteval_user_symbols = {"PropsSI": PropsSI, "tocelcius": tocelsius, "tokelvin": tokelvin}


def matproperty(t_min, t_max):
    """
    Material property decorator object.

    Checks that input T vector is within bounds. Handles floats and arrays.
    """

    def decorator(f):
        def wrapper(*args, **kwargs):
            temperatures = list_array(args[1])

            if not (temperatures <= t_max).all():
                raise ValueError(
                    "Material property not valid outside of tempe"
                    f"rature range: {temperatures} > Tmax = {t_max}"
                )
            if not (temperatures >= t_min).all():
                raise ValueError(
                    "Material property not valid outside of tempe"
                    f"rature range: {temperatures} < Tmin = {t_min}"
                )
            temperatures = array_or_num(temperatures)
            return f(args[0], temperatures, **kwargs)

        return wrapper

    return decorator


def _raise_error():
    raise NotImplementedError(
        "This Material has not yet been given this property. Please add it."
    )


def _try_calc_property(mat, prop_name, *args, **kwargs):
    if not hasattr(mat, prop_name):
        raise MaterialsError(
            f"Property {prop_name} does not exist for material {mat.name}"
        )

    if getattr(mat, prop_name) is not None:
        return getattr(mat, prop_name)(*args, **kwargs)
    else:
        raise MaterialsError(
            f"Property {prop_name} has not been defined for material {mat.name}"
        )


class MaterialProperty:
    """
    Defines a property of a material within a valid temperature range.

    Parameters
    ----------
    value: Union[float, str]
        If supplied as a string then this will define a temperature-, pressure-, and/or
        eps_vol-dependent calculation to be evaluated when the property is retrieved,
        otherwise it will define a constant value.
    temp_max_kelvin: float
        The maximum temperature [K] at which the property is valid. If not provided
        and no temp_max_celcius then all temperatures above 0K are valid.
    temp_min_kelvin: float
        The maximum temperature [K] at which the property is valid. If not
        provided and no temp_min_celcius then properties will be valid down to 0K.
    temp_max_celcius: float
        The maximum temperature [°C] at which the property is valid. If not provided
        and no temp_max_kelvin then all temperatures above 0K are valid.
    temp_min_celcius: float
        The optional maximum temperature [°C] at which the property is valid. If not
        provided and no temp_min_kelvin then properties will be valid down to 0K.
    reference: str
        The optional reference e.g. paper/database/website for the property.
    """

    def __init__(
        self,
        value,
        temp_max_kelvin=None,
        temp_min_kelvin=None,
        temp_max_celcius=None,
        temp_min_celcius=None,
        reference=None,
    ):
        if (temp_max_kelvin is not None or temp_min_kelvin is not None) and (
            temp_max_celcius is not None or temp_min_celcius is not None
        ):
            raise MaterialsError(
                "Material property temperature ranges must be set by either K or C, not both."
            )

        self.value = value
        self.reference = reference

        self.temp_max = None
        if temp_max_kelvin is not None:
            self.temp_max = temp_max_kelvin
        elif temp_max_celcius is not None:
            self.temp_max = tokelvin(temp_max_celcius)

        self.temp_min = None
        if temp_min_kelvin is not None:
            self.temp_min = temp_min_kelvin
        elif temp_min_celcius is not None:
            self.temp_min = tokelvin(temp_min_celcius)

    def __call__(self, temperature, pressure=None, eps_vol=None):
        """
        Evaluates the property at a given temperature, pressure, and/or eps_vol.

        Parameters
        ----------
        temperature: float
            The temperature [K].
        pressure: float
            The optional pressure [Pa].
        esp_vol: float
            The optional cell volume [m^3].

        Returns
        -------
        prop_val: float
            The property evaluated at the given temperature, pressure, and/or eps_vol.
        """
        if isinstance(self.value, str):
            aeval = asteval.Interpreter(usersyms=asteval_user_symbols)
            temperature = list_array(temperature)
            self._validate_temperature(temperature)
            aeval.symtable["temperature"] = temperature
            aeval.symtable["temperature_in_K"] = temperature
            aeval.symtable["temperature_in_C"] = tocelsius(temperature)

            if pressure is not None:
                aeval.symtable["pressure"] = pressure
                aeval.symtable["pressure_in_Pa"] = pressure

            if eps_vol is not None:
                aeval.symtable["eps_vol"] = eps_vol
            else:
                aeval.symtable["eps_vol"] = 0.0

            prop_val = aeval.eval(self.value)
            prop_val = array_or_num(prop_val)

            if len(aeval.error) > 0:
                raise aeval.error[0].exc(aeval.error[0].msg)

            return prop_val
        else:
            self._validate_temperature(temperature)
            return self.value

    @classmethod
    def deserialise(cls, prop_rep):
        """
        Deserialise the provided property representation.

        Parameters
        ----------
        prop_rep: Union[Dict[str, Any], float, str]
            The representation of the property. Can be just the value that the property
            defines, or can be a dictionary containing the value and any of the optional
            properties.

        Returns
        -------
        prop: MaterialProperty
            The `MaterialProperty` corresponding to the provided representation.
        """
        if isinstance(prop_rep, dict):
            return cls(**prop_rep)
        else:
            return cls(value=prop_rep)

    def serialise(self):
        """
        Serialise the material property to a value or dictionary.

        Returns
        -------
        serialised_prop: Union[Dict[str, Any], float, str]
            The serialised representation of the property. Represented by a dictionary
            mapping attributes to their values, if more attributes than the value are
            defined, otherwise just returns the value.
        """
        if self.temp_max is None and self.temp_min is None and self.reference is None:
            return self.value
        else:
            prop_dict = {"value": self.value}
            if self.temp_max is not None:
                prop_dict["temp_max_kelvin"] = self.temp_max
            if self.temp_min is not None:
                prop_dict["temp_min_kelvin"] = self.temp_min
            if self.reference is not None:
                prop_dict["reference"] = self.reference
            return prop_dict

    def _validate_temperature(self, temperature):
        """
        Check that the property is valid for the requested temperature range.

        Parameters
        ----------
        temperature: Union[float, List[float], np.array]
            The temperatures requested to value the property at.

        Raises
        ------
        ValueError
            If any of the requested temperatures are outside of the valid range
        """
        temperatures = list_array(temperature)
        if self.temp_min is not None:
            if (temperatures < self.temp_min).any():
                raise ValueError(
                    "Material property not valid outside of temperature range: "
                    f"{temperatures} < Tmin = {self.temp_min}"
                )
        if self.temp_max is not None:
            if (temperatures > self.temp_max).any():
                raise ValueError(
                    "Material property not valid outside of temperature range: "
                    f"{temperature} > Tmax = {self.temp_max}"
                )


class SerialisedMaterial:
    """
    A mix-in class to make a material serialisable.

    The class must provide attributes to be serialised as annotations.
    """

    def to_dict(self):
        """
        Get a dictionary representation of the material.

        Returns
        -------
        mat_dict : dict
            The dictionary representation of the material.
        """
        attr_dict = {}
        for attr in [attr for attr in self.__annotations__.keys() if attr != "name"]:
            attr_val = getattr(self, attr, None)
            if attr_val is not None:
                if isinstance(attr_val, MaterialProperty):
                    attr_dict[attr] = attr_val.serialise()
                else:
                    attr_dict[attr] = attr_val
        mat_dict = {self.name: attr_dict}
        return mat_dict

    @classmethod
    def from_dict(cls, name, materials_dict):
        """
        Generate an instance of the material from a dictionary of materials.

        Returns
        -------
        material : SerialisedMaterial
            The material.
        """
        mat_dict = materials_dict[name]
        for attr_name, attr_type in cls.__annotations__.items():
            if (
                attr_name in mat_dict
                and not hasattr(attr_type, "__origin__")
                and issubclass(attr_type, MaterialProperty)
            ):
                mat_dict[attr_name] = attr_type.deserialise(mat_dict[attr_name])
        return cls(name, **mat_dict)

    def to_json(self):
        """
        Get a JSON representation of the material.

        Returns
        -------
        data : str
            The JSON representation of the material.
        """
        mat_dict = self.to_dict()
        mat_dict[self.name]["material_class"] = self.__class__.__name__
        return json.dumps(mat_dict)

    @classmethod
    def from_json(cls, data):
        """
        Generate an instance of the material from JSON.

        Returns
        -------
        data : str
            The JSON representation of the material.
        """
        mat_dict = json.loads(data)
        mat_name = list(mat_dict.keys())[0]
        return cls.from_dict(mat_name, mat_dict)

    def __hash__(self):
        """
        Hash the material by it's name.

        Returns
        -------
        hash: int
            The hashed material name
        """
        return hash(self.name)

    def __eq__(self, other):
        """
        Two materials are equal if their attributes have the same values.

        Returns
        -------
        equality: bool
            True if the two materials have the same attribute values, else false.
        """
        return self.to_dict() == other.to_dict()

    def __neq__(self, other):
        """
        Two materials are not equal if their attributes have different values.

        Returns
        -------
        non_equality: bool
            True if the two materials have different attribute values, else false.
        """
        return not (self == other)


class Void(SerialisedMaterial, nmm.Material):
    """
    Void material class.

    Parameters
    ----------
    name: str
        The material's name.
    temperature_in_K: float
        The temperature [K].
    zaid_suffix: str
        The nuclear library to apply to the zaid, for example ".31c", this is used in
        MCNP and Serpent material cards.
    material_id: int
        The id number or mat number used in the MCNP and OpenMC material cards.
    """

    name: str
    temperature_in_K: float  # noqa (N815)
    zaid_suffix: str
    material_id: str

    def __init__(
        self,
        name,
        temperature_in_K=T_DEFAULT,  # noqa(N803)
        zaid_suffix=None,
        material_id=None,
    ):
        super().__init__(
            material_tag=name,
            density=1,
            density_unit="atom/cm3",
            elements={"H": 1},
            percent_type="ao",
            temperature_in_K=temperature_in_K,
            temperature_in_C=tocelsius(temperature_in_K),
            zaid_suffix=zaid_suffix,
            material_id=material_id,
        )

        self.name = name

    def __str__(self):
        """
        Get a string representation of the Void.
        """
        return self.name

    def E(self, temperature=None):  # noqa (N802)
        """
        Young's modulus.

        Parameters
        ----------
        temperature: float
            The optional temperature [K].

        Returns
        -------
        youngs_modulus: float
            The Young's modulus of the material at the given temperature.
        """
        return 0.0

    def mu(self, temperature=None):
        """
        Poisson's ratio.

        Parameters
        ----------
        temperature: float
            The optional temperature [K].

        Returns
        -------
        poissons_ratio: float
            Poisson's ratio for the material at the given temperature.
        """
        return 0.0

    def rho(self, temperature=None):
        """
        Density.

        Parameters
        ----------
        temperature: float
            The optional temperature [K].

        Returns
        -------
        density: float
            The density of the material at the given temperature.
        """
        return 0.0


class MassFractionMaterial(SerialisedMaterial, nmm.Material):
    """
    Mass fraction material

    Parameters
    ----------
    name: str
        The material's name.
    elements: Dict[str, float]
        The constituent elements and their corresponding mass fractions.
    density: MaterialProperty
        The density. If supplied as a string then this will define a
        temperature-dependent calculation, otherwise it will define a constant value.
    density_unit: str
        The unit that the density is supplied in, may be any one of kg/m3, g/cm3, g/cc,
        by default kg/m3.
    temperature_in_K: float
        The temperature [K].
    zaid_suffix: str
        The nuclear library to apply to the zaid, for example ".31c", this is used in
        MCNP and Serpent material cards.
    material_id: int
        The id number or mat number used in the MCNP and OpenMC material cards.
    poissons_ratio: MaterialProperty
        Poisson's ratio. If supplied as a string then this will define a
        temperature-dependent calculation, otherwise it will define a constant value.
    thermal_conductivity: MaterialProperty
        Thermal conductivity [W.m/K]. If supplied as a string then this will define a
        temperature-dependent calculation, otherwise it will define a constant value.
    youngs_modulus: MaterialProperty
        Young's modulus [GPa]. If supplied as a string then this will define a
        temperature-dependent calculation, otherwise it will define a constant value.
    specific_heat: MaterialProperty
        Specific heat [J/kg/K]. If supplied as a string then this will define a
        temperature-dependent calculation, otherwise it will define a constant value.
    coefficient_thermal_expansion: MaterialProperty
        CTE [10^-6/T]. If supplied as a string then this will define a
        temperature-dependent calculation, otherwise it will define a constant value.
    electrical_resistivity: MaterialProperty
        Electrical resistivity [(10^-8)Ohm.m]. If supplied as a string then this will
        define a temperature-dependent calculation, otherwise it will define a constant
        value.
    magnetic_saturation: MaterialProperty
        Magnetic saturation [Am^2/kg]. If supplied as a string then this will define a
        temperature-dependent calculation, otherwise it will define a constant value.
    viscous_remanent_magnetisation: MaterialProperty
        Viscous remanent magnetisation [Am^2/kg]. If supplied as a string then this will
        define a temperature-dependent calculation, otherwise it will define a constant
        value.
    coercive_field: MaterialProperty
        Coercive field [A/m]. If supplied as a string then this will define a
        temperature-dependent calculation, otherwise it will define a constant value.
    minimum_yield_stress: MaterialProperty
        Minimum yield stress [MPa]. If supplied as a string then this will define a
        temperature-dependent calculation, otherwise it will define a constant value.
    average_yield_stress: MaterialProperty
        Average yield stress [MPa]. If supplied as a string then this will define a
        temperature-dependent calculation, otherwise it will define a constant value.
    minimum_ultimate_tensile_stress: MaterialProperty
        Minimum ultimate tensile stress [MPa]. If supplied as a string then this will
        define a temperature-dependent calculation, otherwise it will define a constant
        value.
    average_ultimate_tensile_stress: MaterialProperty
        Average ultimate tensile stress [MPa]. If supplied as a string then this will
        define a temperature-dependent calculation, otherwise it will define a constant
        value.
    """

    # Properties to interface with neutronics material maker
    name: str
    elements: typing.Dict[str, float]
    density: MaterialProperty
    density_unit: str
    temperature_in_K: float  # noqa (N815)
    zaid_suffix: str
    material_id: str

    # Engineering properties
    poissons_ratio: MaterialProperty
    thermal_conductivity: MaterialProperty
    youngs_modulus: MaterialProperty
    specific_heat: MaterialProperty
    coefficient_thermal_expansion: MaterialProperty
    electrical_resistivity: MaterialProperty
    magnetic_saturation: MaterialProperty
    viscous_remanent_magnetisation: MaterialProperty
    coercive_field: MaterialProperty
    minimum_yield_stress: MaterialProperty
    average_yield_stress: MaterialProperty
    minimum_ultimate_tensile_stress: MaterialProperty
    average_ultimate_tensile_stress: MaterialProperty

    def __init__(
        self,
        name,
        elements,
        density=None,
        density_unit="kg/m3",
        temperature_in_K=T_DEFAULT,  # noqa(N803)
        zaid_suffix=None,
        material_id=None,
        poissons_ratio=None,
        thermal_conductivity=None,
        youngs_modulus=None,
        specific_heat=None,
        coefficient_thermal_expansion=None,
        electrical_resistivity=None,
        magnetic_saturation=None,
        viscous_remanent_magnetisation=None,
        coercive_field=None,
        minimum_yield_stress=None,
        average_yield_stress=None,
        minimum_ultimate_tensile_stress=None,
        average_ultimate_tensile_stress=None,
    ):
        if density is None:
            raise MaterialsError("No density (value or T-function) specified.")

        if density_unit not in ["kg/m3", "g/cm3", "g/cc"]:
            raise MaterialsError("Density unit must be one of kg/m3, g/cm3, or g/cc")

        if isinstance(density.value, (int, float)):
            density_val = density.value
            density_equation = None
        else:
            density_val = None
            density_equation = density.value

        super().__init__(
            material_tag=name,
            elements=elements,
            density=density_val,
            density_equation=density_equation,
            density_unit=density_unit,
            percent_type="wo",
            temperature_in_K=temperature_in_K,
            temperature_in_C=tocelsius(temperature_in_K),
            zaid_suffix=zaid_suffix,
            material_id=material_id,
        )

        self.name = name

        self.density_prop = density
        self.poissons_ratio = poissons_ratio
        self.thermal_conductivity = thermal_conductivity
        self.youngs_modulus = youngs_modulus
        self.specific_heat = specific_heat
        self.coefficient_thermal_expansion = coefficient_thermal_expansion
        self.electrical_resistivity = electrical_resistivity
        self.magnetic_saturation = magnetic_saturation
        self.viscous_remanent_magnetisation = viscous_remanent_magnetisation
        self.coercive_field = coercive_field
        self.minimum_yield_stress = minimum_yield_stress
        self.average_yield_stress = average_yield_stress
        self.minimum_ultimate_tensile_stress = minimum_ultimate_tensile_stress
        self.average_ultimate_tensile_stress = average_ultimate_tensile_stress

        if self.density is None:
            self.density = _try_calc_property(self, "density_prop", temperature_in_K)

    def __str__(self):
        """
        Get a string representation of the MfMaterial.
        """
        return self.name

    def make_mat_dict(self, temperature):
        """
        Makes a material dictionary for use in simple beam FE solver

        Parameters
        ----------
        temperature: float
            The temperature in Kelvin

        Returns
        -------
        mat_dict: dict
            The simplified dictionary of material properties
        """
        mat_dict = {
            "E": self.E(temperature) * 1e9,
            "nu": self.mu(temperature),
            "alpha": self.CTE(temperature),
            "rho": self.rho(temperature),
            "sigma_y": self.Sy(temperature),
        }
        return mat_dict

    def mu(self, temperature):
        """
        Poisson's ratio
        """
        return _try_calc_property(self, "poissons_ratio", temperature)

    def k(self, temperature):
        """
        Thermal conductivity in W.m/K
        """
        return _try_calc_property(self, "thermal_conductivity", temperature)

    def E(self, temperature):  # noqa (N802)
        """
        Young's modulus in GPa
        """
        return _try_calc_property(self, "youngs_modulus", temperature)

    def Cp(self, temperature):  # noqa (N802)
        """
        Specific heat in J/kg/K
        """
        return _try_calc_property(self, "specific_heat", temperature)

    def CTE(self, temperature):  # noqa (N802)
        """
        Mean coefficient of thermal expansion in 10**-6/T
        """
        return _try_calc_property(self, "coefficient_thermal_expansion", temperature)

    def rho(self, temperature):
        """
        Mass density in kg/m**3
        """
        density = _try_calc_property(self, "density_prop", temperature)

        if self.density_unit in ["g/cm3", "g/cc"]:
            density = gcm3tokgm3(density)

        return density

    def erho(self, temperature):
        """
        Electrical resistivity in 10^(-8)Ohm.m
        """
        return _try_calc_property(self, "electrical_resistivity", temperature)

    def Ms(self, temperature):  # noqa (N802)
        """
        Magnetic saturation in Am^2/kg
        """
        return _try_calc_property(self, "magnetic_saturation", temperature)

    def Mt(self, temperature):  # noqa (N802)
        """
        Viscous remanent magnetisation in Am^2/kg
        """
        return _try_calc_property(self, "viscous_remanent_magnetisation", temperature)

    def Hc(self, temperature):  # noqa (N802)
        """
        Coercive field in A/m
        """
        return _try_calc_property(self, "coercive_field", temperature)

    def Sy(self, temperature):  # noqa (N802)
        """
        Minimum yield stress in MPa
        """
        return _try_calc_property(self, "minimum_yield_stress", temperature)

    def Syavg(self, temperature):  # noqa (N802)
        """
        Average yield stress in MPa
        """
        return _try_calc_property(self, "average_yield_stress", temperature)

    def Su(self, temperature):  # noqa (N802)
        """
        Minimum ultimate tensile stress in MPa
        """
        return _try_calc_property(self, "minimum_ultimate_tensile_stress", temperature)

    def Suavg(self, temperature):  # noqa (N802)
        """
        Average ultimate tensile stress in MPa
        """
        return _try_calc_property(self, "average_ultimate_tensile_stress", temperature)

    @property
    def temperature(self):
        """
        Temperature: this is a pythonic property, but not an actual material
        property!

        Returns
        -------
        temperature: float
            The temperature in Kelvin
        """
        return self.temperature_in_K

    @temperature.setter
    def temperature(self, value):
        """
        Sets the temperature of the material

        Parameters
        ----------
        value: float
            The temperature in Kelvin
        """
        try:
            self.density = self.rho(value)
        except NotImplementedError:
            pass
        self.temperature_in_K = value
        self.temperature_in_C = tocelsius(value)


class Superconductor:
    """
    Presently gratutious use of multiple inheritance to convey plot function
    and avoid repetition. In future perhaps also a useful thing.
    """

    def plot(self, bmin, bmax, tmin, tmax, eps=None, n=101, m=100):
        """
        Plots superconducting surface parameterisation
        strain `eps` only used for Nb3Sn
        """
        jc = np.zeros([m, n])
        fields = np.linspace(bmin, bmax, n)
        temperatures = np.linspace(tmin, tmax, m)
        for j, b in enumerate(fields):
            for i, t in enumerate(temperatures):
                args = (b, t, eps) if eps else (b, t)
                jc[i, j] = self.Jc(*args)
        fig = plt.figure()
        fields, temperatures = np.meshgrid(fields, temperatures)
        ax = fig.add_subplot(111, projection="3d")
        ax.set_title(self.name)
        ax.set_xlabel("B [T]")
        ax.set_ylabel("T [K]")
        ax.set_zlabel("$j_{c}$ [A/mm^2]")
        ax.plot_surface(fields, temperatures, jc, cmap=plt.cm.viridis)
        ax.view_init(30, 45)

    def Jc(self):  # noqa (N802)
        _raise_error()

    @staticmethod
    def _handle_ij(number):
        """
        Takes the real part of the imagniary number that results from
        exponing a negative number with a fraction
        """
        # return np.sqrt(number.real**2+number.imag**2)
        return number.real


class NbTiSuperconductor(MassFractionMaterial, Superconductor):
    """
    Niobium-Titanium superconductor class.
    """

    __annotations__ = MassFractionMaterial.__annotations__.copy()
    c_0: float
    bc_20: float
    tc_0: float
    alpha: float
    beta: float
    gamma: float

    def __init__(
        self,
        name,
        elements,
        c_0=None,
        bc_20=None,
        tc_0=None,
        alpha=None,
        beta=None,
        gamma=None,
        density=None,
        density_unit="kg/m3",
        temperature_in_K=T_DEFAULT,  # noqa(N803)
        zaid_suffix=None,
        material_id=None,
        poissons_ratio=None,
        thermal_conductivity=None,
        youngs_modulus=None,
        specific_heat=None,
        coefficient_thermal_expansion=None,
        electrical_resistivity=None,
        magnetic_saturation=None,
        viscous_remanent_magnetisation=None,
        coercive_field=None,
        minimum_yield_stress=None,
        average_yield_stress=None,
        minimum_ultimate_tensile_stress=None,
        average_ultimate_tensile_stress=None,
    ):
        super().__init__(
            name=name,
            elements=elements,
            density=density,
            density_unit=density_unit,
            temperature_in_K=temperature_in_K,
            zaid_suffix=zaid_suffix,
            material_id=material_id,
            poissons_ratio=poissons_ratio,
            thermal_conductivity=thermal_conductivity,
            youngs_modulus=youngs_modulus,
            specific_heat=specific_heat,
            coefficient_thermal_expansion=coefficient_thermal_expansion,
            electrical_resistivity=electrical_resistivity,
            magnetic_saturation=magnetic_saturation,
            viscous_remanent_magnetisation=viscous_remanent_magnetisation,
            coercive_field=coercive_field,
            minimum_yield_stress=minimum_yield_stress,
            average_yield_stress=average_yield_stress,
            minimum_ultimate_tensile_stress=minimum_ultimate_tensile_stress,
            average_ultimate_tensile_stress=average_ultimate_tensile_stress,
        )

        self.c_0 = c_0
        self.bc_20 = bc_20
        self.tc_0 = tc_0
        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma

    def Bc2(self, temperature):  # noqa (N802)
        """
        Critical field \n
        :math:`B_{C2}^{*}(T) = B_{C20}(1-(\\frac{T}{T_{C0}})^{1.7})`
        """
        return self.bc_20 * (1 - (temperature / self.tc_0) ** 1.7)

    def Jc(self, B, temperature):  # noqa (N802)
        """
        Critical current \n
        :math:`j_{c}(B, T) = \\frac{C_{0}}{B}(1-(\\frac{T}{T_{C0}})^{1.7})
        ^{\\gamma}(\\frac{B}{B_{C2}(T)})^{\\alpha}(1-(\\frac{B}{B_{C2}(T)}))
        ^{\\beta}`
        """
        a = self.c_0 / B * (1 - (temperature / self.tc_0) ** 1.7) ** self.gamma
        ii = B / self.Bc2(temperature)
        b = ii ** self.alpha
        # The below is an "elegant" dodge of numpy RuntimeWarnings encountered
        # when raising a negative number to a fractional power, which in this
        # parameterisation only occurs if a non-physical (<0) current density
        # is returned.
        # TODO: Check the above..
        c = (1 - ii) ** self.beta if 1 - ii > 0 else 0
        return a * b * c


class NbSnSuperconductor(MassFractionMaterial, Superconductor):
    """
    Niobium-Tin Superconductor class.

    Parameters
    ----------
    temperature_in_K: float
        The temperature [K].
    density: float
        The optional density [kg/m3]. If supplied then this will override the calculated
        density for the material.
    zaid_suffix: str
        The nuclear library to apply to the zaid, for example ".31c", this is used in
        MCNP and Serpent material cards.
    material_id: int
        The id number or mat number used in the MCNP and OpenMC material cards.
    """

    __annotations__ = MassFractionMaterial.__annotations__.copy()
    c_a1: float
    c_a2: float
    eps_0a: float
    eps_m: float
    b_c20m: float
    t_c0max: float
    c: float
    p: float
    q: float

    def __init__(
        self,
        name,
        elements,
        c_a1=None,
        c_a2=None,
        eps_0a=None,
        eps_m=None,
        b_c20m=None,
        t_c0max=None,
        c=None,
        p=None,
        q=None,
        density=None,
        density_unit="kg/m3",
        temperature_in_K=T_DEFAULT,  # noqa(N803)
        zaid_suffix=None,
        material_id=None,
        poissons_ratio=None,
        thermal_conductivity=None,
        youngs_modulus=None,
        specific_heat=None,
        coefficient_thermal_expansion=None,
        electrical_resistivity=None,
        magnetic_saturation=None,
        viscous_remanent_magnetisation=None,
        coercive_field=None,
        minimum_yield_stress=None,
        average_yield_stress=None,
        minimum_ultimate_tensile_stress=None,
        average_ultimate_tensile_stress=None,
    ):
        super().__init__(
            name=name,
            elements=elements,
            density=density,
            density_unit=density_unit,
            temperature_in_K=temperature_in_K,
            zaid_suffix=zaid_suffix,
            material_id=material_id,
            poissons_ratio=poissons_ratio,
            thermal_conductivity=thermal_conductivity,
            youngs_modulus=youngs_modulus,
            specific_heat=specific_heat,
            coefficient_thermal_expansion=coefficient_thermal_expansion,
            electrical_resistivity=electrical_resistivity,
            magnetic_saturation=magnetic_saturation,
            viscous_remanent_magnetisation=viscous_remanent_magnetisation,
            coercive_field=coercive_field,
            minimum_yield_stress=minimum_yield_stress,
            average_yield_stress=average_yield_stress,
            minimum_ultimate_tensile_stress=minimum_ultimate_tensile_stress,
            average_ultimate_tensile_stress=average_ultimate_tensile_stress,
        )

        self.c_a1 = c_a1
        self.c_a2 = c_a2
        self.eps_0a = eps_0a
        self.eps_m = eps_m
        self.b_c20m = b_c20m
        self.t_c0max = t_c0max
        self.c = c
        self.p = p
        self.q = q

        self.eps_sh = self.c_a2 * self.eps_0a / np.sqrt(self.c_a1 ** 2 - self.c_a2 ** 2)

    def Tc_star(self, B, eps):  # noqa (N802)
        """
        Critical temperature

        :math:`T_{C}^{*}(B, {\\epsilon}) = T_{C0max}^{*}s({\\epsilon})^{1/3}
        (1-b_{0})^{1/1.52}`
        """
        if B == 0:
            return self.t_c0max * self.s(eps) ** (1 / 3)
        else:
            b = (1 - self.Bc2_star(0, eps)) ** (1 / 1.52j)
            b = self._handle_ij(b)
            return self.t_c0max * self.s(eps) ** (1 / 3) * b

    def Bc2_star(self, temperature, eps):  # noqa (N802)
        """
        Critical field

        :math:`B_{C}^{*}(T, {\\epsilon}) = B_{C20max}^{*}s({\\epsilon})
        (1-t^{1.52})`
        """
        if temperature == 0:
            return self.b_c20m * self.s(eps)
        else:
            return self.b_c20m * self.s(eps) * (1 - (self._t152(temperature, eps)))

    def Jc(self, B, temperature, eps):  # noqa (N802)
        """
        Critical current

        :math:`j_{c} = \\frac{C}{B}s({\\epsilon})(1-t^{1.52})(1-t^{2})b^{p}
        (1-b)^{q}`
        """
        b = self.b(B, temperature, eps)
        t = self.reduced_t(temperature, eps)
        # Ensure physical current density with max (j, 0)
        # Limits of paramterisation likely to be encountered sooner
        return max(
            (
                self.c
                / B
                * self.s(eps)
                * (1 - self._t152(temperature, eps))
                * (1 - t ** 2)
                * b ** self.p
            )
            * (1 - b ** self.q),
            0,
        )

    def _t152(self, temperature, eps):
        # 1.52 = 30000/19736
        t = self.reduced_t(temperature, eps) ** 1.52j
        t = self._handle_ij(t)
        return t

    def reduced_t(self, temperature, eps):
        """
        Reduced temperature \n
        :math:`t = \\frac{T}{T_{C}^{*}(0, {\\epsilon})}`
        """
        return temperature / self.Tc_star(0, eps)

    def b(self, field, temperature, eps):
        """
        Reduced magnetic field \n
        :math:`b = \\frac{B}{B_{C2}^{*}(0,{\\epsilon})}`
        """
        return field / self.Bc2_star(temperature, eps)

    def s(self, eps):
        """
        Strain function \n
        :math:`s({\\epsilon}) = 1+ \\frac{1}{1-C_{a1}{\\epsilon}_{0,a}}[C_{a1}
        (\\sqrt{{\\epsilon}_{sk}^{2}+{\\epsilon}_{0,a}^{2}}-\\sqrt{({\\epsilon}-
        {\\epsilon}_{sk})^{2}+{\\epsilon}_{0,a}^{2}})-C_{a2}{\\epsilon}]`
        """
        return 1 + 1 / (1 - self.c_a1 * self.eps_0a) * (
            self.c_a1
            * (
                np.sqrt(self.eps_sh ** 2 + self.eps_0a ** 2)
                - np.sqrt((eps - self.eps_sh) ** 2 + self.eps_0a ** 2)
            )
            - self.c_a2 * eps
        )


class Liquid(SerialisedMaterial, nmm.Material):
    """
    Liquid material base class.

    Parameters
    ----------
    temperature_in_K: float
        The temperature [K].
    pressure_in_Pa: float
        The pressure [Pa].
    zaid_suffix: str
        The nuclear library to apply to the zaid, for example ".31c", this is used in
        MCNP and Serpent material cards.
    material_id: int
        The id number or mat number used in the MCNP and OpenMC material cards.
    """

    name: str
    symbol: str
    density: MaterialProperty
    density_unit: str
    temperature_in_K: float  # noqa(N815)
    pressure_in_Pa: float  # noqa(N815)
    zaid_suffix: str
    material_id: str

    def __init__(
        self,
        name,
        symbol,
        density=None,
        density_unit="kg/m3",
        temperature_in_K=T_DEFAULT,  # noqa(N803)
        pressure_in_Pa=P_DEFAULT,  # noqa(N803)
        zaid_suffix=None,
        material_id=None,
    ):
        if density is None:
            raise MaterialsError("No density (value or T/P-function) specified.")

        if density_unit not in ["kg/m3", "g/cm3", "g/cc"]:
            raise MaterialsError("Density unit must be one of kg/m3, g/cm3, or g/cc")

        if isinstance(density.value, (int, float)):
            density_val = density.value
            density_equation = None
        else:
            density_val = None
            density_equation = density.value

        super().__init__(
            material_tag=symbol,
            chemical_equation=symbol,
            density=density_val,
            density_equation=density_equation,
            density_unit=density_unit,
            percent_type="ao",
            temperature_in_K=temperature_in_K,
            temperature_in_C=tocelsius(temperature_in_K),
            pressure_in_Pa=pressure_in_Pa,
            zaid_suffix=zaid_suffix,
            material_id=material_id,
        )

        self.name = name
        self.density_prop = density

        if self.density is None:
            self.density = _try_calc_property(
                self, "density_prop", temperature_in_K, pressure_in_Pa
            )

    def __str__(self):
        """
        Get a string representation of the Liquid.
        """
        return self.name

    def rho(self, temperature, pressure=None):
        """
        Mass density in kg/m**3
        """
        if pressure is None:
            pressure = self.pressure_in_Pa

        density = _try_calc_property(self, "density_prop", temperature, pressure)

        if self.density_unit in ["g/cm3", "g/cc"]:
            density = gcm3tokgm3(density)

        return density

    def E(self, temperature=None):  # noqa (N802)
        """
        Youngs modulus (0 for all liquids)
        """
        return 0

    def mu(self, temperature=None):
        """
        Hmm... not sure about this one
        """
        return 0

    @property
    def pressure(self):
        """
        The pressure of the material in Pascals

        Returns
        -------
        pressure: float
            The pressure [Pa]
        """
        return self.pressure_in_Pa

    @pressure.setter
    def pressure(self, value):
        """
        Sets the pressure of the material

        Parameters
        ----------
        value: float
            The value of the pressure in Pascals
        """
        try:
            self.density = self.rho(self.temperature_in_K, value)
        except NotImplementedError:
            pass
        self.pressure_in_Pa = value

    @property
    def temperature(self):
        """
        Temperature: this is a pythonic property, but not an actual material
        property!

        Returns
        -------
        temperature: float
            The temperature in Kelvin
        """
        return self.temperature_in_K

    @temperature.setter
    def temperature(self, value):
        """
        Sets the temperature of the material

        Parameters
        ----------
        value: float
            The temperature in Kelvin
        """
        try:
            self.density = self.rho(value, self.pressure)
        except NotImplementedError:
            pass
        self.temperature_in_K = value


class UnitCellCompound(SerialisedMaterial, nmm.Material):
    """
    Unit cell compound

    Parameters
    ----------
    temperature_in_K: float
        The temperature [K].
    packing_fraction: 0  <= float <= 1
        Compound packing fraction (filled with Void).
    enrichment: 0 <= float <= 1
        Li6 absolute enrichment fraction.
    zaid_suffix: str
        The nuclear library to apply to the zaid, for example ".31c", this is used in
        MCNP and Serpent material cards.
    material_id: int
        The id number or mat number used in the MCNP and OpenMC material cards.
    """

    # Properties to interface with neutronics material maker
    name: str
    symbol: str
    volume_of_unit_cell_cm3: float
    atoms_per_unit_cell: float
    packing_fraction: float
    enrichment: float
    temperature_in_K: float  # noqa(N815)
    zaid_suffix: str
    material_id: str

    # Engineering properties
    specific_heat: MaterialProperty
    coefficient_thermal_expansion: MaterialProperty

    def __init__(
        self,
        name,
        symbol,
        volume_of_unit_cell_cm3,
        atoms_per_unit_cell,
        packing_fraction=1.0,
        enrichment=None,
        temperature_in_K=T_DEFAULT,  # noqa(N803)
        zaid_suffix=None,
        material_id=None,
        specific_heat=None,
        coefficient_thermal_expansion=None,
    ):
        self.is_enrichable = True
        try:
            import openmc  # noqa(F401)
        except ImportError:
            self.is_enrichable = False
        if enrichment is not None:
            bluemira_warn(
                f"Enrichment set for {self.name} but OpenMC is not available, so "
                "enrichment properties will not be ignored."
            )

        super().__init__(
            material_tag=name,
            chemical_equation=symbol,
            volume_of_unit_cell_cm3=volume_of_unit_cell_cm3,
            atoms_per_unit_cell=atoms_per_unit_cell,
            percent_type="ao",
            temperature_in_K=temperature_in_K,
            temperature_in_C=tocelsius(temperature_in_K),
            packing_fraction=packing_fraction,
            enrichment=enrichment if self.is_enrichable else None,
            enrichment_target="Li6" if self.is_enrichable else None,
            enrichment_type="ao" if self.is_enrichable else None,
            density_unit="g/cm3",
            zaid_suffix=zaid_suffix,
            material_id=material_id,
        )

        self.name = name

        self.specific_heat = specific_heat
        self.coefficient_thermal_expansion = coefficient_thermal_expansion

    def __str__(self):
        """
        Get a string representation of the UcCompound.
        """
        return self.name

    def Cp(self, temperature):  # noqa (N802)
        """
        Specific heat in J/kg/K
        """
        return _try_calc_property(self, "specific_heat", temperature)

    def CTE(self, temperature, eps_vol=None):  # noqa (N802)
        """
        Mean coefficient of thermal expansion in 10**-6/T
        """
        return _try_calc_property(
            self, "coefficient_thermal_expansion", temperature, eps_vol
        )


class BePebbleBed(UnitCellCompound):
    """
    Beryllium Pebble Bed.
    """

    @matproperty(t_min=tokelvin(25), t_max=tokelvin(800))
    def CTE(self, temperature, eps_vol=0):  # noqa (N802)
        """
        https://www.sciencedirect.com/science/article/pii/S0920379602001655
        """
        # NOTE: Effect of inelastic volumetric strains [%] not neglible
        # esp_vol calculated roughly as f(T), as per 2M2BH9
        temperature = tocelsius(temperature)
        if eps_vol == 0:

            def calc_eps_vol(temp):
                """
                Calculates inelastic volumetric strains [%] based on T (C)
                """
                if temp >= 600:
                    return 0.5
                elif temp >= 500:
                    return 0.3
                elif temp < 500:
                    return 0.2

            eps_vol = np.vectorize(calc_eps_vol)(temperature)
        if is_num(eps_vol):
            eps_vol = eps_vol * np.ones_like(temperature)
        return (
            1.81
            + 0.0012 * temperature
            - 5e-7 * temperature ** 2
            + eps_vol
            * (
                9.03
                - 1.386e-3 * temperature
                - 7.6e-6 * temperature ** 2
                + 2.1e-9 * temperature ** 3
            )
        )


class Plasma(SerialisedMaterial, nmm.Material):
    """
    A generic plasma material.
    """

    name: str
    isotopes: typing.Dict[str, float]
    density: MaterialProperty
    density_unit: str
    temperature_in_K: float  # noqa(N815)
    zaid_suffix: str
    material_id: str

    def __init__(
        self,
        name,
        isotopes,
        density=MaterialProperty(1e-6),
        density_unit="g/cm3",
        temperature_in_K=None,  # noqa(N803)
        zaid_suffix=None,
        material_id=None,
    ):
        temperature_in_C = None  # noqa(N806)
        if temperature_in_K is not None:
            temperature_in_C = tocelsius(temperature_in_K)  # noqa(N806)

        density_val = None
        if isinstance(density.value, (int, float)):
            density_val = density.value

        super().__init__(
            material_tag=name,
            density=density_val,
            density_unit=density_unit,
            isotopes=isotopes,
            percent_type="ao",
            temperature_in_K=temperature_in_K,
            temperature_in_C=temperature_in_C,
            material_id=material_id,
            zaid_suffix=zaid_suffix,
        )

        self.name = name

    def __str__(self):
        """
        Get a string representation of the plasma.
        """
        return self.name

    def E(self, temperature=None):  # noqa (N802)
        """
        Young's modulus.
        """
        return 0

    def mu(self, temperature=None):
        """
        Poisson's ratio.
        """
        return 0


if __name__ == "__main__":
    from BLUEPRINT import test

    test()
