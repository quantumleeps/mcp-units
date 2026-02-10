from mcp_units.server import mcp


def test_server_exists() -> None:
    assert mcp.name == "mcp-units"
