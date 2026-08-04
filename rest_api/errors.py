"""Maps internal failures to a clean external HTTP contract -- no internal
exception detail (ES query bodies, MCP stack traces) ever leaks to the caller.
"""
from fastapi import Request
from fastapi.responses import JSONResponse


class MCPUnavailableError(Exception):
    """The internal MCP server could not be reached at all."""


class MCPToolError(Exception):
    """The MCP server reached us but a tool call itself failed."""


class NotFoundError(Exception):
    def __init__(self, code: str, detail: str):
        self.code = code
        self.detail = detail


def register_exception_handlers(app):
    @app.exception_handler(MCPUnavailableError)
    async def _mcp_unavailable(request: Request, exc: MCPUnavailableError):
        return JSONResponse(status_code=503, content={"error": "search_unavailable"})

    @app.exception_handler(MCPToolError)
    async def _mcp_tool_error(request: Request, exc: MCPToolError):
        return JSONResponse(status_code=500, content={"error": "internal_error"})

    @app.exception_handler(NotFoundError)
    async def _not_found(request: Request, exc: NotFoundError):
        return JSONResponse(status_code=404, content={"error": exc.code, "detail": exc.detail})
