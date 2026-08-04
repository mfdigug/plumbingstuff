"""Hybrid BM25 + kNN product search via Elasticsearch's `rrf` retriever, with a
deliberately relative, uncalibrated confidence score layered on top (real vendor
relevance scores are essentially never well-calibrated either).
"""
from common.settings import settings
from mcp_backend.embeddings import embed_text
from mcp_backend.es_client import get_es_client

BM25_FIELDS = ["name^3", "search_terms^2", "description", "brand^2"]
RRF_K = 50
RRF_NUM_CANDIDATES = 200
RRF_RANK_WINDOW_SIZE = 50
RRF_RANK_CONSTANT = 20

# Empirically (see git history), this embedding model's raw cosine similarity
# for short e-commerce phrases sits in a narrow, mostly content-independent band
# regardless of true relevance -- "banana" scores *higher* against a kitchen
# mixer than a genuinely-related-but-untagged toilet query scores against an
# actual toilet. There is no absolute (or relative) kNN-score threshold that
# separates real matches from noise in this data. BM25 (literal/fuzzy/slang
# keyword overlap) is the only reliable signal for "is this relevant at all" --
# kNN is still used for ranking/confidence among BM25-matched candidates, just
# not as a gate on its own.


def _standard_query(query, category):
    bool_query = {"should": [{"multi_match": {"query": query, "fields": BM25_FIELDS, "type": "best_fields", "fuzziness": "AUTO"}}]}
    if category:
        bool_query["filter"] = [{"term": {"category": category}}]
    return {"bool": bool_query}


def _minmax_normalize(scores_by_sku):
    if not scores_by_sku:
        return {}
    values = list(scores_by_sku.values())
    lo, hi = min(values), max(values)
    if hi == lo:
        return {sku: 1.0 for sku in scores_by_sku}
    return {sku: (score - lo) / (hi - lo) for sku, score in scores_by_sku.items()}


def _raw_bm25_scores(es, skus, standard_query):
    body_query = dict(standard_query)
    body_query["bool"] = dict(body_query["bool"])
    body_query["bool"]["filter"] = body_query["bool"].get("filter", []) + [{"terms": {"sku": skus}}]
    resp = es.search(index=settings.es_index_products, query=body_query, size=len(skus))
    return {hit["_source"]["sku"]: hit["_score"] for hit in resp["hits"]["hits"]}


def _raw_knn_scores(es, skus, query_vector):
    resp = es.search(
        index=settings.es_index_products,
        knn={
            "field": "embedding",
            "query_vector": query_vector,
            "k": len(skus),
            "num_candidates": max(len(skus) * 2, 50),
            "filter": {"terms": {"sku": skus}},
        },
        size=len(skus),
    )
    return {hit["_source"]["sku"]: hit["_score"] for hit in resp["hits"]["hits"]}


def _match_reason(query, source, bm25_norm, knn_norm):
    query_lower = query.lower()
    matched_terms = [t for t in source.get("search_terms", []) if t.lower() in query_lower]
    if matched_terms:
        return f"matched search_terms: {', '.join(repr(t) for t in matched_terms)}"
    if source["brand"].lower() in query_lower:
        return f"brand match: {source['brand']}"
    if bm25_norm >= knn_norm:
        return "matched on name/description keywords"
    return "semantic match on description"


def search_products(query, category=None, max_results=20):
    es = get_es_client()
    query_vector = embed_text(query)
    standard_query = _standard_query(query, category)

    knn_retriever = {
        "knn": {
            "field": "embedding",
            "query_vector": query_vector,
            "k": RRF_K,
            "num_candidates": RRF_NUM_CANDIDATES,
        }
    }
    if category:
        knn_retriever["knn"]["filter"] = {"term": {"category": category}}

    resp = es.search(
        index=settings.es_index_products,
        retriever={
            "rrf": {
                "retrievers": [{"standard": {"query": standard_query}}, knn_retriever],
                "rank_window_size": RRF_RANK_WINDOW_SIZE,
                "rank_constant": RRF_RANK_CONSTANT,
            }
        },
        size=max_results,
    )

    hits = resp["hits"]["hits"]
    if not hits:
        return []

    skus = [hit["_source"]["sku"] for hit in hits]
    raw_bm25 = _raw_bm25_scores(es, skus, standard_query)
    raw_knn = _raw_knn_scores(es, skus, query_vector)

    relevant_hits = [hit for hit in hits if raw_bm25.get(hit["_source"]["sku"], 0.0) > 0.0]
    if not relevant_hits:
        return []

    relevant_skus = [hit["_source"]["sku"] for hit in relevant_hits]
    bm25_norm = _minmax_normalize({sku: raw_bm25[sku] for sku in relevant_skus if sku in raw_bm25})
    knn_norm = _minmax_normalize({sku: raw_knn[sku] for sku in relevant_skus if sku in raw_knn})

    candidates = []
    for hit in relevant_hits:
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


def search_items(queries, category=None, max_results_per_item=4):
    groups = []
    for query in queries:
        matches = search_products(query, category=category, max_results=max_results_per_item)
        groups.append({"query": query, "matches": matches, "match_count": len(matches)})
    return groups
