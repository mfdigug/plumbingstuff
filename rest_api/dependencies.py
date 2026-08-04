from fastapi import Request


def get_mcp_client(request: Request):
    return request.app.state.mcp_client
