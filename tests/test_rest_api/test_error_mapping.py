import pytest

from rest_api.errors import MCPUnavailableError
from rest_api.mcp_client import MCPBackendClient


async def test_mcp_unreachable_raises_mcp_unavailable():
    client = MCPBackendClient(server_url="http://127.0.0.1:1/mcp")
    with pytest.raises(MCPUnavailableError):
        await client.product_search("basin tap")


def test_product_search_missing_query_is_422(client):
    resp = client.post("/api/v1/product-search", json={})
    assert resp.status_code == 422
