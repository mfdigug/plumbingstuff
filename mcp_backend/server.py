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
from mcp_backend.search import search_products as _search_products

mcp = FastMCP("plumbing-mock-backend", host=settings.mcp_server_host, port=settings.mcp_server_port)


@mcp.tool()
def search_catalogue(
    query: str | None = None,
    category: str | None = None,
    max_results: int = 20,
    candidate_skus: list[str] | None = None,
    filters: RefineFilters | None = None,
) -> dict:
    """Search or narrow the product catalog -- one tool, two ways to call it:

    - TO SEARCH: pass `query` (a customer's free-text or slang phrase, e.g. "leaky
      loo cistern" or "need a new mixer tap, maybe Caroma") and leave
      `candidate_skus` unset. Returns up to `max_results` ranked candidates under
      `results`, each with a 0-1 `confidence` score (relative to this query only --
      not a calibrated probability) and a `match_reason`. Results are NOT pruned to
      only strong matches: the tail may be weak, so use `confidence` and
      `match_reason` to judge fit rather than assuming the top result is correct.
      `category` optionally restricts to one top-level catalog category (e.g.
      "Taps & Mixers", "Toilets & Cisterns", "Hot Water Systems").

    - TO NARROW a previous search's results: pass `candidate_skus` (the `sku`
      values from a prior call's `results`) plus `filters` -- brand, size, finish,
      color, material, connection_type, price_min, price_max -- and/or a new
      `query` to re-rank within that narrowed set. `results` is an EMPTY list if
      the filters eliminate every candidate; that is a real outcome ("no matches
      after narrowing"), not an error -- never fall back to the unfiltered set
      when this happens.
    """
    if candidate_skus:
        filter_dict = (filters or RefineFilters()).model_dump(exclude_none=True)
        return {"results": _refine_candidates(candidate_skus, filter_dict, query=query)}

    if not query:
        raise ValueError("search_catalogue requires `query` when `candidate_skus` is not provided")
    return {"results": _search_products(query, category=category, max_results=max_results)}


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
