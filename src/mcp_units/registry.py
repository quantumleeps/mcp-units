import warnings

import pint

ureg = pint.UnitRegistry()


def get_all_compatible_units(dimensionality: pint.util.UnitsContainer) -> list[str]:
    """Return all canonical unit names matching a dimensionality.

    Pint's built-in get_compatible_units() returns an incomplete subset
    (e.g., 14 of 45 length units, missing foot/inch/yard). This iterates
    the full registry and deduplicates aliases to canonical names.
    """
    seen: dict[str, str] = {}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        for attr in dir(ureg):
            if attr.startswith("_"):
                continue
            try:
                unit = getattr(ureg, attr)
                if (
                    hasattr(unit, "dimensionality")
                    and unit.dimensionality == dimensionality
                ):
                    canonical = str(ureg.Unit(attr))
                    if canonical not in seen:
                        seen[canonical] = attr
            except Exception:
                continue
    return sorted(seen.keys())


def get_systems() -> list[str]:
    """Return all unit system names from the registry."""
    return sorted(attr for attr in dir(ureg.sys) if not attr.startswith("_"))


def get_system_units(system: str) -> list[str]:
    """Return all unit names belonging to a unit system."""
    sys_obj = getattr(ureg.sys, system, None)
    if sys_obj is None:
        return []
    return sorted(attr for attr in dir(sys_obj) if not attr.startswith("_"))


def get_dimensions() -> list[str]:
    """Return all unique non-dimensionless dimensionalities in the registry."""
    dims: set[str] = set()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        for attr in dir(ureg):
            if attr.startswith("_"):
                continue
            try:
                unit = getattr(ureg, attr)
                if hasattr(unit, "dimensionality"):
                    d = str(unit.dimensionality)
                    if d and d != "dimensionless":
                        dims.add(d)
            except Exception:
                continue
    return sorted(dims)
