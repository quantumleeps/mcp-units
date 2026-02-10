from dataclasses import dataclass


@dataclass
class ConversionResult:
    input_value: float
    input_unit: str
    output_value: float
    output_unit: str
    conversion_factor: float
    dimensionality: str


@dataclass
class ConversionError:
    input_unit: str
    target_unit: str
    input_dimensionality: str
    target_dimensionality: str
    error: str


@dataclass
class CompatibilityResult:
    unit_a: str
    unit_b: str
    compatible: bool
    dimensionality_a: str
    dimensionality_b: str
    explanation: str


@dataclass
class ParseResult:
    magnitude: float
    units: str
    dimensionality: str
    si_equivalent_value: float
    si_equivalent_unit: str


@dataclass
class ParseError:
    expression: str
    error: str


@dataclass
class CompatibleUnits:
    unit: str
    dimensionality: str
    compatible_units: list[str]


@dataclass
class SimplifyResult:
    input_expression: str
    simplified: str
    base_units: str
    dimensionality: str


@dataclass
class SimplifyError:
    expression: str
    error: str
