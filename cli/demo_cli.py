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


def print_candidates(matches):
    if not matches:
        print("    (no matches)")
        return
    for m in matches:
        print(f"    {m['sku']:16s} conf={m['confidence']:.2f}  ${m['price_aud']:<8}  {m['name']}")
        print(f"                     -- {m['match_reason']}")


def print_search_results(item_groups):
    """Prints each item's matches; returns all matched SKUs flattened, for the
    `refine` command's convenience (refine narrows whichever SKUs you pass it)."""
    all_skus = []
    for group in item_groups:
        print(f"  \"{group['query']}\" ({group['match_count']} matches):")
        print_candidates(group["matches"])
        all_skus.extend(m["sku"] for m in group["matches"])
    return all_skus


def print_stock(locations):
    for loc in locations:
        eta = f" eta={loc['eta_days']}d" if loc.get("eta_days") else ""
        print(f"  {loc['store_name']:26s} {loc['state']:4s} qty={loc['qty_on_hand']:<3} status={loc['status']}{eta}")


def print_help():
    print(
        "Commands:\n"
        "  search <item> [| <item> ...]             (one or more items, e.g. search toilet lid | tap)\n"
        "  refine <attr=value> [<attr=value> ...]   (narrows candidates from last search)\n"
        "  stock <sku> [state]\n"
        "  customer <customer_id>\n"
        "  cart add <customer_id> <sku> [qty]\n"
        "  cart view <customer_id>\n"
        "  cart remove <customer_id> <sku>\n"
        "  quit\n"
    )


def _parse_items(text):
    return [s.strip() for s in text.split("|") if s.strip()]


def _parse_filters(text):
    filters = {}
    for pair in text.split():
        key, _, value = pair.partition("=")
        if key:
            filters[key] = value
    return filters


async def run_rest():
    candidate_skus = []
    async with httpx.AsyncClient(base_url=REST_BASE_URL, timeout=30) as client:
        while True:
            try:
                cmd = input("\n> ").strip()
            except EOFError:
                break
            if not cmd or cmd in ("quit", "exit"):
                break

            try:
                if cmd.startswith("search "):
                    items = _parse_items(cmd[len("search "):])
                    resp = await client.post("/search_catalogue", json={"items": items})
                    resp.raise_for_status()
                    candidate_skus = print_search_results(resp.json()["results"])
                elif cmd.startswith("refine "):
                    filters = _parse_filters(cmd[len("refine "):])
                    resp = await client.post(
                        "/search_catalogue", json={"candidate_skus": candidate_skus, "filters": filters}
                    )
                    resp.raise_for_status()
                    candidate_skus = print_search_results(resp.json()["results"])
                elif cmd.startswith("stock "):
                    parts = cmd[len("stock "):].split()
                    params = {"sku": parts[0]}
                    if len(parts) > 1:
                        params["state"] = parts[1]
                    resp = await client.get("/availability", params=params)
                    if resp.status_code == 404:
                        print("  SKU not found")
                        continue
                    resp.raise_for_status()
                    print_stock(resp.json()["locations"])
                elif cmd.startswith("customer "):
                    resp = await client.get(f"/customers/{cmd[len('customer '):].strip()}")
                    if resp.status_code == 404:
                        print("  customer not found")
                        continue
                    resp.raise_for_status()
                    print(f"  {resp.json()}")
                elif cmd.startswith("cart add "):
                    parts = cmd[len("cart add "):].split()
                    customer_id, sku = parts[0], parts[1]
                    qty = int(parts[2]) if len(parts) > 2 else 1
                    resp = await client.post(f"/cart/{customer_id}/items", json={"sku": sku, "quantity": qty})
                    print(f"  {resp.json()}")
                elif cmd.startswith("cart view "):
                    resp = await client.get(f"/cart/{cmd[len('cart view '):].strip()}")
                    print(f"  {resp.json()}")
                elif cmd.startswith("cart remove "):
                    parts = cmd[len("cart remove "):].split()
                    customer_id, sku = parts[0], parts[1]
                    resp = await client.delete(f"/cart/{customer_id}/items/{sku}")
                    print(f"  {resp.json()}")
                elif cmd == "help":
                    print_help()
                else:
                    print("  unrecognized command, type 'help'")
            except httpx.HTTPStatusError as exc:
                print(f"  HTTP {exc.response.status_code}: {exc.response.text}")


async def run_via_mcp():
    from mcp_backend.availability import check_availability
    from mcp_backend.refine import refine_candidates
    from mcp_backend.search import search_items

    candidate_skus = []
    while True:
        try:
            cmd = input("\n(mcp)> ").strip()
        except EOFError:
            break
        if not cmd or cmd in ("quit", "exit"):
            break

        if cmd.startswith("search "):
            groups = search_items(_parse_items(cmd[len("search "):]))
            candidate_skus = print_search_results(groups)
        elif cmd.startswith("refine "):
            matches = refine_candidates(candidate_skus, _parse_filters(cmd[len("refine "):]))
            candidate_skus = [m["sku"] for m in matches]
            print_candidates(matches)
        elif cmd.startswith("stock "):
            parts = cmd[len("stock "):].split()
            state = parts[1] if len(parts) > 1 else None
            print_stock(check_availability(parts[0], state=state))
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
