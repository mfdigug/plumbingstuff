"""Generate per (sku, store) stock docs from data/generated/products.jsonl and
data/seed/store_locations.yaml.

Writes data/generated/stock.jsonl. Absence of a doc for a sku+store pair means
"never carried here" — that's intentional and distinct from qty_on_hand: 0
("out of stock"); this script simply omits docs for pairs that fail the carry roll.
"""
import argparse
import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

SEED_DIR = Path(__file__).resolve().parent.parent / "data" / "seed"
GEN_DIR = Path(__file__).resolve().parent.parent / "data" / "generated"

CARRY_PROBABILITY = {"flagship": 0.85, "mid": 0.60, "regional": 0.35}
SPECIAL_ORDER_PROBABILITY = 0.05
QTY_WEIGHTS = [(0, 0.15), (1, 0.15), (2, 0.15), (3, 0.15), (5, 0.15), (8, 0.10), (15, 0.10), (30, 0.05)]


def weighted_qty(rng):
    values = [q for q, _ in QTY_WEIGHTS]
    weights = [w for _, w in QTY_WEIGHTS]
    return rng.choices(values, weights=weights, k=1)[0]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    rng = random.Random(args.seed)

    with open(SEED_DIR / "store_locations.yaml") as f:
        stores = yaml.safe_load(f)["stores"]

    products_path = GEN_DIR / "products.jsonl"
    products = [json.loads(line) for line in open(products_path)]

    now = datetime.now(timezone.utc)
    stock_docs = []

    for product in products:
        for store in stores:
            carry_probability = CARRY_PROBABILITY[store["tier"]]
            if rng.random() > carry_probability:
                continue  # not carried at this store — no doc written

            qty = weighted_qty(rng)
            if qty == 0:
                status = "out_of_stock"
                eta_days = None
            elif rng.random() < SPECIAL_ORDER_PROBABILITY:
                status = "special_order"
                eta_days = rng.randint(3, 14)
            else:
                status = "in_stock"
                eta_days = None

            staleness_days = rng.randint(0, 6)
            last_updated = (now - timedelta(days=staleness_days)).isoformat()

            stock_docs.append(
                {
                    "sku": product["sku"],
                    "store_id": store["store_id"],
                    "store_name": store["store_name"],
                    "suburb": store["suburb"],
                    "state": store["state"],
                    "postcode": store["postcode"],
                    "qty_on_hand": qty,
                    "status": status,
                    "eta_days": eta_days,
                    "last_updated": last_updated,
                }
            )

    GEN_DIR.mkdir(parents=True, exist_ok=True)
    out_path = GEN_DIR / "stock.jsonl"
    with open(out_path, "w") as f:
        for doc in stock_docs:
            f.write(json.dumps(doc) + "\n")

    print(f"Wrote {len(stock_docs)} stock docs to {out_path}")


if __name__ == "__main__":
    main()
