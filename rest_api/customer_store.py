"""Customer profile reads go straight to Elasticsearch -- no MCP round trip,
since this is an exact-match lookup, not a search/matching concern.
"""
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
