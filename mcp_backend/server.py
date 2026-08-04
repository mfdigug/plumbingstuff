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
from mcp_backend.refine import refine_candidates as _refine_candidates
from mcp_backend.schemas import RefineFilters
from mcp_backend.search import search_items as _search_items

mcp = FastMCP("plumbing-mock-backend", host=settings.mcp_server_host, port=settings.mcp_server_port)


@mcp.tool()
def search_catalogue(
    items: list[str] | None = None,
    category: str | None = None,
    max_results_per_item: int = 4,
    candidate_skus: list[str] | None = None,
    filters: RefineFilters | None = None,
    query: str | None = None,
) -> dict:
    """Search or narrow the product catalog -- one tool, two ways to call it:

    - TO SEARCH: pass `items`, an array of free-text/slang phrases -- ONE entry
      per distinct product the customer asked for. A customer asking for "10
      toilet lids and 3 taps" becomes `items=["toilet lid", "tap"]`; a single
      item still goes in as a one-element array, e.g. `items=["mixer tap"]`.
      Returns one result group per input item under `results`, each capped at
      `max_results_per_item` ranked candidates under `matches` (default 4), with
      a 0-1 `confidence` score (relative to that item's own query only -- not a
      calibrated probability) and a `match_reason`. Matches are NOT pruned to
      only strong ones: the tail may be weak, so use `confidence` and
      `match_reason` to judge fit rather than assuming the top match is correct.
      `category` optionally restricts every item's search to one top-level
      catalog category (e.g. "Taps & Mixers", "Toilets & Cisterns").

    - TO NARROW a previous search's results for ONE item: pass `candidate_skus`
      (the `sku` values from one item's `matches` in a prior call) plus
      `filters` -- brand, size, finish, color, material, connection_type,
      price_min, price_max -- and/or a new `query` string to re-rank within that
      narrowed set. Still returns the same shape (`results` with one group).
      That group's `matches` is EMPTY if the filters eliminate every candidate;
      that is a real outcome ("no matches after narrowing"), not an error --
      never fall back to the unfiltered set when this happens.
    """
    if candidate_skus:
        filter_dict = (filters or RefineFilters()).model_dump(exclude_none=True)
        matches = _refine_candidates(candidate_skus, filter_dict, query=query)
        return {"results": [{"query": query or "", "matches": matches, "match_count": len(matches)}]}

    if not items:
        raise ValueError("search_catalogue requires `items` when `candidate_skus` is not provided")
    return {"results": _search_items(items, category=category, max_results_per_item=max_results_per_item)}


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
