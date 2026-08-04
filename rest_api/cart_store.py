"""Customer/cart reads and writes go straight to Elasticsearch -- no MCP round
trip, since these are exact-match lookups and simple document writes, not a
search/matching concern.
"""
from datetime import datetime, timezone

from elasticsearch import NotFoundError as ESNotFoundError

from common.settings import settings
from mcp_backend.es_client import get_es_client
from rest_api.errors import NotFoundError


def get_customer(customer_id):
    es = get_es_client()
    try:
        doc = es.get(index=settings.es_index_customers, id=customer_id)
    except ESNotFoundError:
        raise NotFoundError("customer_not_found", f"No customer with id '{customer_id}'")
    return doc["_source"]


def _get_cart_doc(customer_id):
    es = get_es_client()
    try:
        doc = es.get(index=settings.es_index_carts, id=customer_id)
        return doc["_source"]
    except ESNotFoundError:
        return {"customer_id": customer_id, "items": [], "updated_at": None}


def product_exists(sku):
    es = get_es_client()
    try:
        es.get(index=settings.es_index_products, id=sku)
        return True
    except ESNotFoundError:
        return False


def _resolve_cart(cart_doc):
    es = get_es_client()
    items = cart_doc.get("items", [])
    if not items:
        return {
            "customer_id": cart_doc["customer_id"],
            "items": [],
            "subtotal_aud": 0.0,
            "updated_at": cart_doc.get("updated_at"),
        }

    skus = [item["sku"] for item in items]
    docs = es.mget(index=settings.es_index_products, ids=skus)
    products_by_sku = {d["_id"]: d["_source"] for d in docs["docs"] if d.get("found")}

    resolved_items = []
    total = 0.0
    for item in items:
        product = products_by_sku.get(item["sku"])
        if product is None:
            continue  # SKU was removed from the catalog after being added -- skip, don't error
        line_subtotal = round(product["price_aud"] * item["quantity"], 2)
        total += line_subtotal
        resolved_items.append(
            {
                "sku": item["sku"],
                "name": product["name"],
                "brand": product["brand"],
                "quantity": item["quantity"],
                "unit_price_aud": product["price_aud"],
                "subtotal_aud": line_subtotal,
                "added_at": item.get("added_at"),
            }
        )

    return {
        "customer_id": cart_doc["customer_id"],
        "items": resolved_items,
        "subtotal_aud": round(total, 2),
        "updated_at": cart_doc.get("updated_at"),
    }


def get_cart(customer_id):
    get_customer(customer_id)  # raises NotFoundError if the customer_id is unknown
    return _resolve_cart(_get_cart_doc(customer_id))


def add_item(customer_id, sku, quantity):
    get_customer(customer_id)
    if not product_exists(sku):
        raise NotFoundError("sku_not_found", f"No product with sku '{sku}'")

    es = get_es_client()
    cart_doc = _get_cart_doc(customer_id)
    now = datetime.now(timezone.utc).isoformat()

    items = cart_doc.get("items", [])
    existing = next((i for i in items if i["sku"] == sku), None)
    if existing:
        existing["quantity"] += quantity
    else:
        items.append({"sku": sku, "quantity": quantity, "added_at": now})

    cart_doc["items"] = items
    cart_doc["updated_at"] = now
    cart_doc["customer_id"] = customer_id

    es.index(index=settings.es_index_carts, id=customer_id, document=cart_doc)
    return _resolve_cart(cart_doc)


def remove_item(customer_id, sku):
    get_customer(customer_id)
    es = get_es_client()
    cart_doc = _get_cart_doc(customer_id)
    items = cart_doc.get("items", [])
    if not any(i["sku"] == sku for i in items):
        raise NotFoundError("sku_not_in_cart", f"SKU '{sku}' is not in this cart")

    cart_doc["items"] = [i for i in items if i["sku"] != sku]
    cart_doc["updated_at"] = datetime.now(timezone.utc).isoformat()
    cart_doc["customer_id"] = customer_id

    es.index(index=settings.es_index_carts, id=customer_id, document=cart_doc)
    return _resolve_cart(cart_doc)
