"""Internal MCP tool server. Never called externally — only rest_api/mcp_client.py
talks to this. Streamable HTTP by default (see plan: shared model/ES-client state
across REST API workers, independent restart/debugging), stdio available via
--transport for quick MCP Inspector sessions.
"""
import argparse

from mcp.server.fastmcp import FastMCP
from starlette.responses import PlainTextResponse

from common.settings import settings
from mcp_backend.availability import check_availability as _check_availability
from mcp_backend.search import product_search as _product_search

mcp = FastMCP("plumbing-mock-backend", host=settings.mcp_server_host, port=settings.mcp_server_port)


@mcp.tool()
def product_search(query: str) -> dict:
    """Extract one or more distinct product requests out of a single free-text
    customer utterance (e.g. "a 90mm stormwater flex and a roll of PTFE tape")
    and search each. Callers do not pre-split items themselves -- this tool
    does the splitting -- and the response carries richer per-item extraction
    metadata (quantity/color/material/semantic search hint) plus both a
    capped `products` match list and a longer `extendedCandidates` tail per
    item.
    """
    return _product_search(query)


@mcp.tool()
def check_availability(
    sku: str, store_id: str | None = None, state: str | None = None, postcode: str | None = None
) -> dict:
    """Check stock for a single SKU across stores. With no filters, `results`
    covers all 15 AU stores. `state` (e.g. "NSW") or `postcode` narrows to a region;
    `store_id` targets one store. Each result's `status` is one of: "in_stock",
    "out_of_stock" (carried here but currently zero on hand), "special_order" (not
    on the shelf but orderable -- see `eta_days`), or "not_carried" (this store
    never stocks this SKU at all). These are meaningfully different things to tell
    a caller -- do not treat "out_of_stock" and "not_carried" as the same thing.
    """
    return {"results": _check_availability(sku, store_id=store_id, state=state, postcode=postcode)}


@mcp.custom_route("/healthz", methods=["GET"])
async def healthz(request):
    return PlainTextResponse("ok")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--transport", choices=["stdio", "streamable-http"], default=settings.mcp_transport)
    parser.add_argument("--host", default=settings.mcp_server_host)
    parser.add_argument("--port", type=int, default=settings.mcp_server_port)
    args = parser.parse_args()

    mcp.settings.host = args.host
    mcp.settings.port = args.port
    mcp.run(transport=args.transport)


if __name__ == "__main__":
    main()
