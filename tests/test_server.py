import json
from typing import Any

import pytest
from fastmcp import Client
from mcp.types import TextContent, TextResourceContents

from mcp_units.server import mcp


@pytest.fixture
def client() -> Client:
    return Client(mcp)


async def call_tool_json(client: Client, name: str, args: dict[str, Any]) -> Any:
    result = await client.call_tool(name, args)
    content = result.content[0]
    assert isinstance(content, TextContent)
    return json.loads(content.text)


def test_server_exists() -> None:
    assert mcp.name == "mcp-units"


class TestToolsViaMCP:
    async def test_convert_meters_to_feet(self, client: Client) -> None:
        async with client:
            data = await call_tool_json(
                client,
                "convert",
                {"value": 1.0, "from_unit": "meter", "to_unit": "foot"},
            )
        assert data["output_value"] == pytest.approx(3.28084, rel=1e-3)
        assert data["output_unit"] == "foot"

    async def test_convert_incompatible(self, client: Client) -> None:
        async with client:
            data = await call_tool_json(
                client,
                "convert",
                {"value": 1.0, "from_unit": "meter", "to_unit": "kilogram"},
            )
        assert "error" in data
        assert "incompatible" in data["error"].lower()

    async def test_convert_undefined_unit(self, client: Client) -> None:
        async with client:
            data = await call_tool_json(
                client,
                "convert",
                {"value": 1.0, "from_unit": "meter", "to_unit": "bogus"},
            )
        assert "error" in data

    async def test_check_compatibility_true(self, client: Client) -> None:
        async with client:
            data = await call_tool_json(
                client,
                "check_compatibility",
                {"unit_a": "psi", "unit_b": "kPa"},
            )
        assert data["compatible"] is True

    async def test_check_compatibility_false(self, client: Client) -> None:
        async with client:
            data = await call_tool_json(
                client,
                "check_compatibility",
                {"unit_a": "meter", "unit_b": "second"},
            )
        assert data["compatible"] is False

    async def test_parse_quantity(self, client: Client) -> None:
        async with client:
            data = await call_tool_json(
                client, "parse_quantity", {"expression": "9.81 m/s^2"}
            )
        assert data["magnitude"] == pytest.approx(9.81)
        assert "[length]" in data["dimensionality"]
        assert "[time]" in data["dimensionality"]

    async def test_parse_quantity_invalid(self, client: Client) -> None:
        async with client:
            data = await call_tool_json(
                client, "parse_quantity", {"expression": "not_a_unit"}
            )
        assert "error" in data

    async def test_list_compatible_units(self, client: Client) -> None:
        async with client:
            data = await call_tool_json(
                client, "list_compatible_units", {"unit": "meter"}
            )
        assert "foot" in data["compatible_units"]
        assert "mile" in data["compatible_units"]

    async def test_simplify(self, client: Client) -> None:
        async with client:
            data = await call_tool_json(client, "simplify", {"expression": "1000 Pa"})
        assert "kilopascal" in data["simplified"]


class TestResourcesViaMCP:
    async def test_systems_index(self, client: Client) -> None:
        async with client:
            result = await client.read_resource("units://systems")
        content = result[0]
        assert isinstance(content, TextResourceContents)
        assert "imperial" in content.text
        assert "mks" in content.text

    async def test_system_units_imperial(self, client: Client) -> None:
        async with client:
            result = await client.read_resource("units://systems/imperial")
        content = result[0]
        assert isinstance(content, TextResourceContents)
        assert "foot" in content.text
        assert "pound" in content.text

    async def test_system_units_unknown(self, client: Client) -> None:
        async with client:
            result = await client.read_resource("units://systems/fake_system")
        content = result[0]
        assert isinstance(content, TextResourceContents)
        assert "Unknown system" in content.text

    async def test_dimensions_index(self, client: Client) -> None:
        async with client:
            result = await client.read_resource("units://dimensions")
        content = result[0]
        assert isinstance(content, TextResourceContents)
        assert "[length]" in content.text
        assert "[mass]" in content.text


class TestPromptsViaMCP:
    async def test_convert_document(self, client: Client) -> None:
        async with client:
            result = await client.get_prompt(
                "convert_document",
                {"document": "The bridge is 100 feet long."},
            )
        content = result.messages[0].content
        assert isinstance(content, TextContent)
        assert "100 feet" in content.text
        assert "SI" in content.text

    async def test_convert_document_custom_system(self, client: Client) -> None:
        async with client:
            result = await client.get_prompt(
                "convert_document",
                {
                    "document": "The tank holds 500 liters.",
                    "target_system": "imperial",
                },
            )
        content = result.messages[0].content
        assert isinstance(content, TextContent)
        assert "500 liters" in content.text
        assert "imperial" in content.text

    async def test_check_calculations(self, client: Client) -> None:
        async with client:
            result = await client.get_prompt(
                "check_calculations",
                {"calculations": "F = 10 kg * 9.81 m/s^2"},
            )
        content = result.messages[0].content
        assert isinstance(content, TextContent)
        assert "10 kg" in content.text
        assert "dimensional consistency" in content.text.lower()
