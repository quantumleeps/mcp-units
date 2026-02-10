import pytest

from mcp_units.registry import get_all_compatible_units, ureg


class TestConvert:
    def test_mg_per_liter_to_g_per_liter(self) -> None:
        source = ureg.Quantity(100, "mg/L")
        target = source.to("g/L")
        assert target.magnitude == pytest.approx(0.1)

    def test_conversion_factor(self) -> None:
        factor = ureg.Quantity(1, "mg/L").to("g/L").magnitude
        assert factor == pytest.approx(0.001)

    def test_dimensionality_preserved(self) -> None:
        source = ureg.Quantity(100, "mg/L")
        assert str(source.dimensionality) == "[mass] / [length] ** 3"

    def test_incompatible_raises(self) -> None:
        source = ureg.Quantity(1, "meter")
        with pytest.raises(Exception):
            source.to("kilogram")

    def test_undefined_unit_raises(self) -> None:
        with pytest.raises(Exception):
            ureg.Quantity(1, "nonsense_unit")


class TestCheckCompatibility:
    def test_psi_compatible_with_kpa(self) -> None:
        assert ureg.Quantity(1, "psi").is_compatible_with(ureg.Quantity(1, "kPa"))

    def test_psi_incompatible_with_gallon(self) -> None:
        assert not ureg.Quantity(1, "psi").is_compatible_with(
            ureg.Quantity(1, "gallon")
        )

    def test_same_unit_compatible(self) -> None:
        assert ureg.Quantity(1, "meter").is_compatible_with(ureg.Quantity(1, "meter"))

    def test_length_units_compatible(self) -> None:
        assert ureg.Quantity(1, "foot").is_compatible_with(
            ureg.Quantity(1, "kilometer")
        )


class TestParseQuantity:
    def test_acceleration(self) -> None:
        q = ureg.parse_expression("9.81 m/s^2")
        assert q.magnitude == pytest.approx(9.81)
        si = q.to_base_units()
        assert si.magnitude == pytest.approx(9.81)
        assert str(si.units) == "meter / second ** 2"

    def test_concentration(self) -> None:
        q = ureg.parse_expression("100 mg/L")
        assert q.magnitude == pytest.approx(100)
        assert "[mass] / [length] ** 3" == str(q.dimensionality)

    def test_invalid_expression_raises(self) -> None:
        with pytest.raises(Exception):
            ureg.parse_expression("not_a_unit")


class TestListCompatibleUnits:
    def test_psi_includes_pascal(self) -> None:
        units = get_all_compatible_units(ureg.Quantity(1, "psi").dimensionality)
        assert "pascal" in units

    def test_length_includes_imperial(self) -> None:
        units = get_all_compatible_units(ureg.Quantity(1, "meter").dimensionality)
        assert "foot" in units
        assert "inch" in units
        assert "yard" in units
        assert "mile" in units

    def test_length_includes_metric(self) -> None:
        units = get_all_compatible_units(ureg.Quantity(1, "meter").dimensionality)
        assert "meter" in units
        assert "kilometer" in units
        assert "centimeter" in units


class TestSimplify:
    def test_compact_prefix(self) -> None:
        q = ureg.parse_expression("1000 Pa")
        compact = q.to_compact()
        assert "kilopascal" in str(compact)

    def test_base_units(self) -> None:
        q = ureg.parse_expression("1000 Pa")
        base = q.to_base_units()
        assert base.magnitude == pytest.approx(1000)
        assert "kilogram" in str(base.units)

    def test_compound_base_units(self) -> None:
        q = ureg.parse_expression("5 kg * m / s^2")
        base = q.to_base_units()
        assert base.magnitude == pytest.approx(5)
