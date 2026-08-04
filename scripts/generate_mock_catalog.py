"""Generate ~500 mock plumbing SKUs from data/seed/{brands,categories,slang_terms}.yaml.

Writes data/generated/products.jsonl (one product dict per line, no embedding yet —
scripts/generate_embeddings.py adds that in a separate pass).
"""
import argparse
import json
import random
from datetime import datetime, timezone
from pathlib import Path

import yaml

SEED_DIR = Path(__file__).resolve().parent.parent / "data" / "seed"
OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "generated"

TIER_MULTIPLIER = {"premium": 1.3, "mid": 1.0, "value": 0.8}
SLANG_ATTACH_PROBABILITY = 0.7
AMBIGUOUS_ATTACH_PROBABILITY = 0.3
MIN_SLANG_TERMS, MAX_SLANG_TERMS = 2, 5


def load_yaml(name):
    with open(SEED_DIR / name) as f:
        return yaml.safe_load(f)


def subcategory_code(key):
    parts = key.split("_")
    if len(parts) == 1:
        return parts[0][:3].upper()
    return "".join(p[0] for p in parts).upper()[:3]


def render_name(template, brand, attributes):
    values = {"brand": brand}
    values.update(attributes)
    return template.format(**{k: v for k, v in values.items() if "{" + k + "}" in template})


def pick_attribute_combo(attribute_options, rng):
    keys = list(attribute_options.keys())
    combo = {}
    for key in keys:
        combo[key] = rng.choice(attribute_options[key])
    return combo


def build_description(name, category_name, brand, attributes, rng):
    bits = [f"{name} from {brand}, suited to {category_name.lower()} applications."]
    extra = [f"{k.replace('_', ' ')}: {v}" for k, v in attributes.items()]
    if extra:
        bits.append("Specifications — " + ", ".join(extra) + ".")
    return " ".join(bits)


def assign_slang(subcat_key, slang_by_subcat, ambiguous_pool, rng):
    terms = []
    pool = slang_by_subcat.get(subcat_key, [])
    if pool and rng.random() < SLANG_ATTACH_PROBABILITY:
        n = min(len(pool), rng.randint(MIN_SLANG_TERMS, MAX_SLANG_TERMS))
        terms.extend(rng.sample(pool, n))
    for term, subcats in ambiguous_pool.items():
        if subcat_key in subcats and rng.random() < AMBIGUOUS_ATTACH_PROBABILITY:
            terms.append(term)
    return sorted(set(terms))


def generate(target_total, seed):
    rng = random.Random(seed)
    brands_data = load_yaml("brands.yaml")["brands"]
    categories_data = load_yaml("categories.yaml")["categories"]
    slang_data = load_yaml("slang_terms.yaml")
    slang_by_subcat = slang_data.get("by_subcategory", {})
    ambiguous_pool = slang_data.get("ambiguous_pool", {})

    total_weight = sum(c["weight"] for c in categories_data)
    now = datetime.now(timezone.utc).isoformat()

    products = []
    sku_counters = {}

    for category in categories_data:
        cat_target = round(category["weight"] / total_weight * target_total)
        subcats = category["subcategories"]
        per_subcat = max(1, cat_target // len(subcats))
        for subcat in subcats:
            attribute_options = subcat.get("attribute_options", {})
            for _ in range(per_subcat):
                brand = rng.choice(brands_data)
                attributes = pick_attribute_combo(attribute_options, rng)
                name = render_name(subcat["name_template"], brand["name"], attributes)
                low, high = category["price_range"]
                base_price = rng.uniform(low, high)
                price = round(base_price * TIER_MULTIPLIER[brand["tier"]] + rng.uniform(-2, 2), 2)
                price = max(price, 1.0)

                brand_prefix = "".join(c for c in brand["name"].upper() if c.isalpha())[:3]
                cat_code = subcategory_code(subcat["key"])
                counter_key = f"{brand_prefix}-{cat_code}"
                sku_counters[counter_key] = sku_counters.get(counter_key, 0) + 1
                sku = f"{counter_key}-{4000 + sku_counters[counter_key]}"

                search_terms = assign_slang(subcat["key"], slang_by_subcat, ambiguous_pool, rng)

                products.append(
                    {
                        "sku": sku,
                        "name": name,
                        "description": build_description(name, category["name"], brand["name"], attributes, rng),
                        "category": category["name"],
                        "subcategory": subcat["name"],
                        "subcategory_key": subcat["key"],
                        "brand": brand["name"],
                        "search_terms": search_terms,
                        "attributes": attributes,
                        "price_aud": price,
                        "created_at": now,
                        "updated_at": now,
                    }
                )

    return products


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--target-total", type=int, default=500)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    products = generate(args.target_total, args.seed)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / "products.jsonl"
    with open(out_path, "w") as f:
        for product in products:
            f.write(json.dumps(product) + "\n")

    print(f"Wrote {len(products)} products to {out_path}")


if __name__ == "__main__":
    main()
