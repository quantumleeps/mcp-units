# mcp-units

An MCP server that provides deterministic unit conversions via [Pint](https://pint.readthedocs.io/). LLMs guess at unit conversions — this server makes them exact.

## What this does

Exposes 5 tools, 3 resources, and 2 prompts over the [Model Context Protocol](https://modelcontextprotocol.io/). Any MCP client (Claude Code, Claude Desktop, Cursor) can convert units, check dimensional compatibility, parse quantity strings, and simplify expressions — all backed by Pint's 400+ unit registry instead of LLM arithmetic.

## How it works

A [FastMCP](https://gofastmcp.com/) server wraps Pint's `UnitRegistry` and exposes it through MCP primitives:

- **Tools** — `convert`, `check_compatibility`, `parse_quantity`, `list_compatible_units`, `simplify`
- **Resources** — `units://systems`, `units://systems/{system}`, `units://dimensions`
- **Prompts** — `convert_document` (extract and convert all quantities in text), `check_calculations` (verify dimensional consistency)

The server runs over stdio by default (for Claude Code / Claude Desktop) or Streamable HTTP via `fastmcp run` (for remote / containerized deployment).

## Quickstart

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)

### Install and run

```bash
git clone https://github.com/quantumleeps/mcp-units.git
cd mcp-units
uv sync
```

### Add to Claude Code

```bash
claude mcp add --transport stdio mcp-units -- \
  uv run --directory /path/to/mcp-units mcp-units
```

### Add to Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "mcp-units": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/mcp-units", "mcp-units"]
    }
  }
}
```

### Run over HTTP

```bash
uv run fastmcp run src/mcp_units/server.py --transport http --port 8000
```

### Docker

```bash
docker build -t mcp-units .
docker run -p 8000:8000 mcp-units
```

### Tests

```bash
uv sync --all-extras
uv run pytest
```

## Project Structure

```
mcp-units/
  src/mcp_units/
    server.py       # FastMCP instance — tools, resources, prompts
    registry.py     # Pint UnitRegistry + compatible units workaround
    models.py       # Result dataclasses for structured tool output
  tests/
    test_tools.py   # 18 Pint logic tests
    test_server.py  # 17 MCP Client integration tests
  Dockerfile        # HTTP transport for containerized deployment
```

## Contributing

PRs welcome. Run `pre-commit install` after cloning and ensure `uv run pytest` passes before submitting.

## License

MIT
