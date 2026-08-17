"""Bulk-load data/generated/*.jsonl into their Elasticsearch indices.

products_with_embeddings.jsonl -> products,
customers.jsonl -> customers (doc _id = customer_id).
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from elasticsearch.helpers import bulk  # noqa: E402

from common.settings import settings  # noqa: E402
from mcp_backend.es_client import get_es_client  # noqa: E402

GEN_DIR = Path(__file__).resolve().parent.parent / "data" / "generated"


def load_jsonl(path):
    with open(path) as f:
        return [json.loads(line) for line in f]


def bulk_index(es, index_name, docs, id_field=None):
    def actions():
        for doc in docs:
            action = {"_index": index_name, "_source": doc}
            if id_field:
                action["_id"] = doc[id_field]
            yield action

    success, errors = bulk(es, actions(), stats_only=False, raise_on_error=False)
    if errors:
        print(f"  {len(errors)} errors indexing into {index_name}: {errors[:3]}")
    print(f"Indexed {success} docs into {index_name}")


def main():
    es = get_es_client()

    products = load_jsonl(GEN_DIR / "products_with_embeddings.jsonl")
    bulk_index(es, settings.es_index_products, products, id_field="sku")

    customers = load_jsonl(GEN_DIR / "customers.jsonl")
    bulk_index(es, settings.es_index_customers, customers, id_field="customer_id")

    es.indices.refresh(index=",".join([settings.es_index_products, settings.es_index_customers]))


if __name__ == "__main__":
    main()
