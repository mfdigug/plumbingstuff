"""Add a 384-dim embedding to every product in data/generated/products.jsonl.

Writes data/generated/products_with_embeddings.jsonl. The same embed_text()
function (mcp_backend/embeddings.py) is used here at index time and later at
query time, so index and query vectors are produced identically.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mcp_backend.embeddings import embed_texts  # noqa: E402

GEN_DIR = Path(__file__).resolve().parent.parent / "data" / "generated"


def product_embedding_text(product):
    parts = [product["name"], product["description"], product["brand"]]
    parts.extend(product.get("search_terms", []))
    return " ".join(parts)


def main():
    products = [json.loads(line) for line in open(GEN_DIR / "products.jsonl")]
    texts = [product_embedding_text(p) for p in products]

    print(f"Embedding {len(texts)} products...")
    vectors = embed_texts(texts)

    out_path = GEN_DIR / "products_with_embeddings.jsonl"
    with open(out_path, "w") as f:
        for product, vector in zip(products, vectors):
            product["embedding"] = vector
            f.write(json.dumps(product) + "\n")

    print(f"Wrote {len(products)} embedded products to {out_path}")


if __name__ == "__main__":
    main()
