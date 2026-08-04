"""Create (or recreate, for dev) the products/stock/customers/carts indices from
mappings/*.json.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.settings import settings  # noqa: E402
from mcp_backend.es_client import get_es_client  # noqa: E402

MAPPINGS_DIR = Path(__file__).resolve().parent.parent / "mappings"

INDEX_TO_MAPPING_FILE = {
    settings.es_index_products: "products_mapping.json",
    settings.es_index_stock: "stock_mapping.json",
    settings.es_index_customers: "customers_mapping.json",
    settings.es_index_carts: "carts_mapping.json",
}


def main():
    es = get_es_client()
    for index_name, mapping_file in INDEX_TO_MAPPING_FILE.items():
        with open(MAPPINGS_DIR / mapping_file) as f:
            body = json.load(f)

        if es.indices.exists(index=index_name):
            es.indices.delete(index=index_name)
            print(f"Deleted existing index: {index_name}")

        es.indices.create(index=index_name, **body)
        print(f"Created index: {index_name}")


if __name__ == "__main__":
    main()
