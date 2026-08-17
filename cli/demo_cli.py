"""Interactive manual-QA REPL. Talks to the REST API by default (closer to how the
real caller -- the voice agent -- experiences it); --via-mcp bypasses the REST
layer and calls mcp_backend functions directly for side-by-side comparison when
tracking down whether a bug is in scoring/ES or in the REST reshaping layer.
"""
import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx  # noqa: E402

REST_BASE_URL = "http://localhost:8080/v1"
# Fixed path -- must match the real backend's contract this mock stands in for.
PRODUCT_SEARCH_URL = "http://localhost:8080/api/v1/product-search"


def print_product_search_results(data):
    print(f"  {data['summary']}")
    for item in data["items"]:
        print(f"  \"{item['itemName']}\" x{item['quantity']} ({item['status']}):")
        for p in item["products"]:
            print(f"    {p['productCode']:16s} [{p['confidenceLevel']:6s}] {p['description']}")
            print(f"      -> {p['rationale']}")
        if item.get("alternates"):
            print(f"    ...{len(item['alternates'])} alternates")


def print_help():
    print(
        "Commands:\n"
        "  psearch <free text query>      (agent-style POST /product-search, e.g. psearch a roll of PTFE tape)\n"
        "  customer <customer_id>\n"
        "  quit\n"
    )


async def run_rest():
    async with httpx.AsyncClient(base_url=REST_BASE_URL, timeout=30) as client:
        while True:
            try:
                cmd = input("\n> ").strip()
            except EOFError:
                break
            if not cmd or cmd in ("quit", "exit"):
                break

            try:
                if cmd.startswith("psearch "):
                    query = cmd[len("psearch "):].strip()
                    resp = await client.post(PRODUCT_SEARCH_URL, json={"query": query, "region": "AU", "branchId": "1234"})
                    resp.raise_for_status()
                    print_product_search_results(resp.json())
                elif cmd.startswith("customer "):
                    resp = await client.get(f"/customers/{cmd[len('customer '):].strip()}")
                    if resp.status_code == 404:
                        print("  customer not found")
                        continue
                    resp.raise_for_status()
                    print(f"  {resp.json()}")
                elif cmd == "help":
                    print_help()
                else:
                    print("  unrecognized command, type 'help'")
            except httpx.HTTPStatusError as exc:
                print(f"  HTTP {exc.response.status_code}: {exc.response.text}")


async def run_via_mcp():
    from mcp_backend.search import product_search

    def _to_camel_response(data):
        from rest_api.schemas import ProductSearchResponse

        return ProductSearchResponse(request_id="local", **data).model_dump(by_alias=True)

    while True:
        try:
            cmd = input("\n(mcp)> ").strip()
        except EOFError:
            break
        if not cmd or cmd in ("quit", "exit"):
            break

        if cmd.startswith("psearch "):
            print_product_search_results(_to_camel_response(product_search(cmd[len("psearch "):].strip())))
        elif cmd == "help":
            print_help()
        else:
            print("  unrecognized command, type 'help'")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--via-mcp", action="store_true", help="bypass the REST API, call mcp_backend directly")
    args = parser.parse_args()

    print_help()
    asyncio.run(run_via_mcp() if args.via_mcp else run_rest())


if __name__ == "__main__":
    main()
