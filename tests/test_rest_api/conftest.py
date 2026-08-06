import socket
import sys
from pathlib import Path
from urllib.parse import urlparse

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from common.settings import settings  # noqa: E402
from rest_api.main import app  # noqa: E402


def _mcp_server_reachable():
    parsed = urlparse(settings.mcp_server_url)
    try:
        with socket.create_connection((parsed.hostname, parsed.port), timeout=1):
            return True
    except OSError:
        return False


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def any_sku():
    from mcp_backend.es_client import get_es_client

    es = get_es_client()
    resp = es.search(index=settings.es_index_products, query={"match_all": {}}, size=1)
    return resp["hits"]["hits"][0]["_source"]["sku"]


@pytest.fixture()
def require_live_stack():
    """Request this in tests that exercise search/availability/cart end to
    end -- they need both Elasticsearch and a running mcp-server, unlike the
    404/422 error-mapping cases which fail before ever reaching MCP.
    """
    if not _mcp_server_reachable():
        pytest.skip(
            "mcp-server not reachable -- run `python -m mcp_backend.server` "
            "(or the `server` compose profile) before running this test."
        )
