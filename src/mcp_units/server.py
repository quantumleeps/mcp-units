import pint
from fastmcp import FastMCP

from mcp_units.models import (
    CompatibilityResult,
    CompatibleUnits,
    ConversionError,
    ConversionResult,
    ParseError,
    ParseResult,
    SimplifyError,
    SimplifyResult,
)
from mcp_units.registry import Q_, get_all_compatible_units, ureg

mcp = FastMCP("mcp-units")


@mcp.tool
def convert(
    value: float, from_unit: str, to_unit: str
) -> ConversionResult | ConversionError:
    """Convert a value from one unit to another.

    Returns the converted value with conversion factor, or a structured error
    if the units are dimensionally incompatible.
    """
    try:
        source = Q_(value, from_unit)
        target = source.to(to_unit)
        factor = Q_(1, from_unit).to(to_unit).magnitude
        return ConversionResult(
            input_value=value,
            input_unit=from_unit,
            output_value=target.magnitude,
            output_unit=str(target.units),
            conversion_factor=factor,
            dimensionality=str(source.dimensionality),
        )
    except pint.DimensionalityError:
        return ConversionError(
            input_unit=from_unit,
            target_unit=to_unit,
            input_dimensionality=str(Q_(1, from_unit).dimensionality),
            target_dimensionality=str(Q_(1, to_unit).dimensionality),
            error=f"Cannot convert {from_unit} to {to_unit}: incompatible dimensions",
        )
    except pint.UndefinedUnitError as e:
        return ConversionError(
            input_unit=from_unit,
            target_unit=to_unit,
            input_dimensionality="unknown",
            target_dimensionality="unknown",
            error=str(e),
        )


@mcp.tool
def check_compatibility(unit_a: str, unit_b: str) -> CompatibilityResult:
    """Check if two units are dimensionally compatible (i.e., can be converted).

    Returns whether the units share the same physical dimension.
    """
    try:
        q_a = Q_(1, unit_a)
        q_b = Q_(1, unit_b)
    except pint.UndefinedUnitError as e:
        return CompatibilityResult(
            unit_a=unit_a,
            unit_b=unit_b,
            compatible=False,
            dimensionality_a="unknown",
            dimensionality_b="unknown",
            explanation=str(e),
        )

    dim_a = str(q_a.dimensionality)
    dim_b = str(q_b.dimensionality)
    compatible = q_a.is_compatible_with(q_b)

    if compatible:
        explanation = f"Both are {dim_a}"
    else:
        explanation = f"{unit_a} is {dim_a}, {unit_b} is {dim_b}"

    return CompatibilityResult(
        unit_a=unit_a,
        unit_b=unit_b,
        compatible=compatible,
        dimensionality_a=dim_a,
        dimensionality_b=dim_b,
        explanation=explanation,
    )


@mcp.tool
def parse_quantity(expression: str) -> ParseResult | ParseError:
    """Parse a quantity string into structured components.

    Accepts expressions like '100 mg/L' or '9.81 m/s²'.
    Returns the magnitude, units, dimensionality, and SI equivalent.
    """
    try:
        q = ureg.parse_expression(expression)
        si = q.to_base_units()
        return ParseResult(
            magnitude=q.magnitude,
            units=str(q.units),
            dimensionality=str(q.dimensionality),
            si_equivalent_value=si.magnitude,
            si_equivalent_unit=str(si.units),
        )
    except (
        pint.UndefinedUnitError,
        pint.errors.DefinitionSyntaxError,
        ValueError,
    ) as e:
        return ParseError(expression=expression, error=str(e))


@mcp.tool
def list_compatible_units(unit: str) -> CompatibleUnits | ParseError:
    """List all units compatible with the given unit.

    Returns every canonical unit name that shares the same physical dimension,
    including imperial and US customary units.
    """
    try:
        q = Q_(1, unit)
    except pint.UndefinedUnitError as e:
        return ParseError(expression=unit, error=str(e))

    unit_names = get_all_compatible_units(q.dimensionality)

    return CompatibleUnits(
        unit=unit,
        dimensionality=str(q.dimensionality),
        compatible_units=unit_names,
    )


@mcp.tool
def simplify(expression: str) -> SimplifyResult | SimplifyError:
    """Simplify a unit expression to its most compact form.

    Adjusts prefixes (e.g., 1000 Pa → 1 kPa) and reduces named units.
    Also provides the base SI representation.
    """
    try:
        q = ureg.parse_expression(expression)
        compact = q.to_compact()
        base = q.to_base_units()
        return SimplifyResult(
            input_expression=expression,
            simplified=str(compact),
            base_units=str(base),
            dimensionality=str(q.dimensionality),
        )
    except (
        pint.UndefinedUnitError,
        pint.errors.DefinitionSyntaxError,
        ValueError,
    ) as e:
        return SimplifyError(expression=expression, error=str(e))


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
