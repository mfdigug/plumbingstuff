"""Per-store stock lookup. Store metadata (name/suburb/state/postcode) is static
reference data, read straight from data/seed/store_locations.yaml rather than a
dedicated ES index — it's configuration, not something that needs to be searched.

Any sku+store pair with no stock doc is synthesized here as status="not_carried"
(never simply omitted), since silence is genuinely ambiguous: "no results" vs.
"we don't stock it here" are different things a caller needs to hear apart.
"""
from pathlib import Path

import yaml

from common.settings import settings
from mcp_backend.es_client import get_es_client

SEED_DIR = Path(__file__).resolve().parent.parent / "data" / "seed"


def _all_stores():
    with open(SEED_DIR / "store_locations.yaml") as f:
        return yaml.safe_load(f)["stores"]


def check_availability(sku, store_id=None, state=None, postcode=None):
    stores = _all_stores()
    if store_id:
        stores = [s for s in stores if s["store_id"] == store_id]
    if state:
        stores = [s for s in stores if s["state"] == state]
    if postcode:
        stores = [s for s in stores if s["postcode"] == postcode]

    if not stores:
        return []

    es = get_es_client()
    resp = es.search(
        index=settings.es_index_stock,
        query={
            "bool": {
                "filter": [
                    {"term": {"sku": sku}},
                    {"terms": {"store_id": [s["store_id"] for s in stores]}},
                ]
            }
        },
        size=len(stores),
    )
    stock_by_store = {hit["_source"]["store_id"]: hit["_source"] for hit in resp["hits"]["hits"]}

    results = []
    for store in stores:
        doc = stock_by_store.get(store["store_id"])
        results.append(
            {
                "sku": sku,
                "store_id": store["store_id"],
                "store_name": store["store_name"],
                "suburb": store["suburb"],
                "state": store["state"],
                "postcode": store["postcode"],
                "qty_on_hand": doc["qty_on_hand"] if doc else 0,
                "status": doc["status"] if doc else "not_carried",
                "eta_days": doc.get("eta_days") if doc else None,
                "last_updated": doc.get("last_updated") if doc else None,
            }
        )
    return results
