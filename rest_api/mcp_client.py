"""MCP client wired to the internal mcp_backend server. Opens a fresh
streamable-HTTP connection per tool call rather than holding one open across
requests: streamablehttp_client/ClientSession hold anyio cancel scopes that are
only safe to enter and exit within a single task, and a REST request handler's
task is not guaranteed to be the same task across separate requests -- trying to
persist a "long-lived" session across them broke with
"Attempted to exit a cancel scope that isn't the current task's current cancel
scope". Per-call connections trade a small amount of handshake overhead for
correctness, which is the right tradeoff at this mock's traffic level.
"""
import json

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from common.settings import settings
from rest_api.errors import MCPToolError, MCPUnavailableError


def _parse_tool_payload(result):
    if result.isError:
        text = "".join(block.text for block in result.content if getattr(block, "type", None) == "text")
        raise MCPToolError(text or "MCP tool call failed")

    if getattr(result, "structuredContent", None) is not None:
        return result.structuredContent

    text_block = next((b for b in result.content if getattr(b, "type", None) == "text"), None)
    if text_block is None:
        raise MCPToolError("MCP tool returned no content")
    return json.loads(text_block.text)


class MCPBackendClient:
    def __init__(self, server_url=None):
        self.server_url = server_url or settings.resolved_mcp_server_url

    async def close(self):
        pass  # nothing held open between calls -- kept for lifespan symmetry

    async def _call_tool_raw(self, name, arguments):
        try:
            async with streamable_http_client(self.server_url) as (read, write, _):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool(name, arguments)
        except MCPToolError:
            raise
        except Exception as exc:
            raise MCPUnavailableError(str(exc)) from exc

        return _parse_tool_payload(result)

    async def product_search(self, query):
        return await self._call_tool_raw("product_search", {"query": query})
