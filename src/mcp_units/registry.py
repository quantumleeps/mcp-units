import warnings

import pint

ureg = pint.UnitRegistry()
Q_ = ureg.Quantity


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
