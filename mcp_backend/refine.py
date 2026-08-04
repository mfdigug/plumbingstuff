"""Narrow a prior set of search candidates by attribute filters (and optionally a
second disambiguating utterance). Returns an empty list — never a silent
unfiltered fallback — if the filters eliminate every candidate.
"""
from common.settings import settings
from mcp_backend.embeddings import embed_text
from mcp_backend.es_client import get_es_client
from mcp_backend.search import (
    BM25_FIELDS,
    RRF_NUM_CANDIDATES,
    RRF_RANK_CONSTANT,
    RRF_RANK_WINDOW_SIZE,
    _match_reason,
    _minmax_normalize,
    _raw_bm25_scores,
    _raw_knn_scores,
)

ATTRIBUTE_FILTER_FIELDS = ["brand", "size", "finish", "color", "material", "connection_type"]


def _filter_clauses(candidate_skus, filters):
    clauses = [{"terms": {"sku": candidate_skus}}]
    for field in ATTRIBUTE_FILTER_FIELDS:
        value = filters.get(field)
        if value is None:
            continue
        es_field = "brand" if field == "brand" else f"attributes.{field}"
        clauses.append({"term": {es_field: value}})

    price_range = {}
    if filters.get("price_min") is not None:
        price_range["gte"] = filters["price_min"]
    if filters.get("price_max") is not None:
        price_range["lte"] = filters["price_max"]
    if price_range:
        clauses.append({"range": {"price_aud": price_range}})

    return clauses


def refine_candidates(candidate_skus, filters, query=None):
    es = get_es_client()
    filter_clauses = _filter_clauses(candidate_skus, filters)

    if not query:
        resp = es.search(
            index=settings.es_index_products,
            query={"bool": {"filter": filter_clauses}},
            size=len(candidate_skus),
        )
        hits = resp["hits"]["hits"]
        return [
            {
                "sku": hit["_source"]["sku"],
                "name": hit["_source"]["name"],
                "brand": hit["_source"]["brand"],
                "category": hit["_source"]["category"],
                "subcategory": hit["_source"]["subcategory"],
                "price_aud": hit["_source"]["price_aud"],
                "attributes": hit["_source"].get("attributes", {}),
                "confidence": 1.0,
                "match_reason": "matched refine filters",
            }
            for hit in hits
        ]

    query_vector = embed_text(query)
    standard_query = {"bool": {"should": [{"multi_match": {"query": query, "fields": BM25_FIELDS, "type": "best_fields", "fuzziness": "AUTO"}}], "filter": filter_clauses}}

    resp = es.search(
        index=settings.es_index_products,
        retriever={
            "rrf": {
                "retrievers": [
                    {"standard": {"query": standard_query}},
                    {
                        "knn": {
                            "field": "embedding",
                            "query_vector": query_vector,
                            "k": len(candidate_skus),
                            "num_candidates": RRF_NUM_CANDIDATES,
                            "filter": {"bool": {"filter": filter_clauses}},
                        }
                    },
                ],
                "rank_window_size": RRF_RANK_WINDOW_SIZE,
                "rank_constant": RRF_RANK_CONSTANT,
            }
        },
        size=len(candidate_skus),
    )

    hits = resp["hits"]["hits"]
    if not hits:
        return []

    skus = [hit["_source"]["sku"] for hit in hits]
    bm25_norm = _minmax_normalize(_raw_bm25_scores(es, skus, standard_query))
    knn_norm = _minmax_normalize(_raw_knn_scores(es, skus, query_vector))

    candidates = []
    for hit in hits:
        source = hit["_source"]
        sku = source["sku"]
        bm25 = bm25_norm.get(sku, 0.0)
        knn = knn_norm.get(sku, 0.0)
        candidates.append(
            {
                "sku": sku,
                "name": source["name"],
                "brand": source["brand"],
                "category": source["category"],
                "subcategory": source["subcategory"],
                "price_aud": source["price_aud"],
                "attributes": source.get("attributes", {}),
                "confidence": round(0.5 * bm25 + 0.5 * knn, 2),
                "match_reason": _match_reason(query, source, bm25, knn),
            }
        )
    return candidates
