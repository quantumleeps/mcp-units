"""MCP tool integration — fetches schemas and executes tools via FastMCP Client."""

import json
import logging
from typing import Any

from fastmcp import Client
from mcp.types import TextContent, Tool

from mcp_units.server import mcp

log = logging.getLogger(__name__)


def mcp_tool_to_anthropic(tool: Tool) -> dict[str, Any]:
    """Convert an MCP Tool to Anthropic API tool format.

    MCP uses camelCase ``inputSchema``, Anthropic uses snake_case ``input_schema``.
    The JSON Schema content is identical.
    """
    return {
        "name": tool.name,
        "description": tool.description or "",
        "input_schema": tool.inputSchema,
    }


class MCPToolExecutor:
    """Wraps FastMCP Client for tool schema retrieval and execution.

    Usage::

        async with MCPToolExecutor() as executor:
            tools = executor.anthropic_tools
            result = await executor.call_tool("convert", {...})
    """

    def __init__(self) -> None:
        self._client = Client(mcp)
        self._tools: list[Tool] = []
        self._anthropic_tools: list[dict[str, Any]] = []

    async def __aenter__(self) -> "MCPToolExecutor":
        await self._client.__aenter__()
        self._tools = await self._client.list_tools()
        self._anthropic_tools = [mcp_tool_to_anthropic(t) for t in self._tools]
        log.info("MCP tools loaded: %s", [t.name for t in self._tools])
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self._client.__aexit__(*exc)

    @property
    def anthropic_tools(self) -> list[dict[str, Any]]:
        """Tool definitions in Anthropic API format."""
        return self._anthropic_tools

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> str:
        """Execute a tool call via MCP and return the JSON result string."""
        try:
            result = await self._client.call_tool(name, arguments)
            content = result.content[0]
            if isinstance(content, TextContent):
                return content.text
            return json.dumps({"error": f"Unexpected content type: {type(content)}"})
        except Exception as e:
            log.warning("MCP tool call failed: %s(%s) -> %s", name, arguments, e)
            return json.dumps({"error": str(e)})
