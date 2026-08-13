"""Generate ~30 mock customers (Faker en_AU — flavor text, not architecturally
significant like store addresses). Every customer starts with an empty cart.

Writes data/generated/customers.jsonl and data/generated/carts.jsonl.
"""
import argparse
import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml
from faker import Faker

SEED_DIR = Path(__file__).resolve().parent.parent / "data" / "seed"
GEN_DIR = Path(__file__).resolve().parent.parent / "data" / "generated"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=30)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    rng = random.Random(args.seed)
    fake = Faker("en_AU")
    fake.seed_instance(args.seed)

    with open(SEED_DIR / "store_locations.yaml") as f:
        stores = yaml.safe_load(f)["stores"]

    now = datetime.now(timezone.utc)
    customers = []
    carts = []

    for i in range(1, args.count + 1):
        customer_id = f"CUST-{i:04d}"
        first_name = fake.first_name()
        last_name = fake.last_name()
        store = rng.choice(stores)
        created_days_ago = rng.randint(10, 900)

        customers.append(
            {
                "customer_id": customer_id,
                "first_name": first_name,
                "last_name": last_name,
                "email": f"{first_name.lower()}.{last_name.lower()}@{fake.free_email_domain()}",
                "phone": fake.phone_number(),
                "preferred_store_id": store["store_id"],
                "address": {
                    "street": fake.street_address(),
                    "suburb": fake.suburb() if hasattr(fake, "suburb") else store["suburb"],
                    "state": store["state"],
                    "postcode": store["postcode"],
                },
                "created_at": (now - timedelta(days=created_days_ago)).isoformat(),
            }
        )

    GEN_DIR.mkdir(parents=True, exist_ok=True)

    with open(GEN_DIR / "customers.jsonl", "w") as f:
        for customer in customers:
            f.write(json.dumps(customer) + "\n")

    with open(GEN_DIR / "carts.jsonl", "w") as f:
        for cart in carts:
            f.write(json.dumps(cart) + "\n")

    print(f"Wrote {len(customers)} customers and {len(carts)} carts to {GEN_DIR}")


if __name__ == "__main__":
    main()
