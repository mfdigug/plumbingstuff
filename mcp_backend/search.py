"""Hybrid BM25 + kNN product search via Elasticsearch's `rrf` retriever, with a
deliberately relative, uncalibrated confidence score layered on top (real vendor
relevance scores are essentially never well-calibrated either).
"""
import hashlib
import time

from common.settings import settings
from mcp_backend.embeddings import embed_text
from mcp_backend.es_client import get_es_client
from mcp_backend.extraction import extract_items

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


# --- product_search: shaped to match the real maX Voice BFF /api/v1/product-search
# contract (see docs/real-backend-contract.md) ---
#
# The real backend runs two retrieval backends fused, then an LLM re-ranking
# pass that writes a categorical confidenceLevel + a quotable rationale per
# product, and groups near-duplicate variants under a familyName. This mock
# has one retrieval path and no LLM call, so all three are derived directly
# from the existing BM25+kNN `confidence`/`match_reason` signal computed in
# search_products() above -- a strong literal/brand hit reads as high
# confidence (-> status "matched"), a weak/semantic-only hit reads as
# medium/low (-> "needs_checking"). This is a mock stand-in only: swap it out
# wholesale once real API access lands, not a design to preserve.
MAX_PRODUCT_SEARCH_ITEMS = 10
DEFAULT_MATCHED_PER_ITEM = 4
DEFAULT_EXTENDED_PER_ITEM = 8
MOCK_ASSET_HOST = "https://mock-assets.internal/products"

# Mock stand-in thresholds for the real LLM re-ranker's confidenceLevel -- tune
# freely, there's nothing sacred about these numbers.
HIGH_CONFIDENCE_THRESHOLD = 0.65
MEDIUM_CONFIDENCE_THRESHOLD = 0.35

# Only a "high" top candidate is confident enough to skip a clarifying question.
CONFIDENCE_LEVEL_TO_STATUS = {"high": "matched", "medium": "needs_checking", "low": "needs_checking"}

# Alternates carry no ranking verdict at all in the real contract -- just
# catalogue display facts.
ALTERNATE_FIELDS = ("product_code", "description", "unit_of_measure", "unit_of_measure2", "pack_ratio", "gst_exempt", "image_url")


def _elapsed_ms(start):
    return round((time.perf_counter() - start) * 1000)


def _brand_code(brand_name):
    # The real backend sends an opaque internal vendor code here, not a
    # display name -- our seed data only has names, so derive a stable
    # numeric-looking stand-in per brand (deterministic across requests/runs,
    # unlike Python's randomized str hash()) so the agent config has to deal
    # with the same "code, not name" shape it'll face against the real system.
    digest = hashlib.md5(brand_name.encode()).hexdigest()
    return str(100000 + (int(digest, 16) % 900) * 1000)


def _unit_of_measure(name):
    name_lower = name.lower()
    if "tape" in name_lower:
        return "ROLL", None, None
    if "pipe" in name_lower:
        return "LEN", "MTR", 6
    return "EA", None, None


def _confidence_level(confidence):
    if confidence >= HIGH_CONFIDENCE_THRESHOLD:
        return "high"
    if confidence >= MEDIUM_CONFIDENCE_THRESHOLD:
        return "medium"
    return "low"


def _rationale(match_reason):
    if match_reason.startswith("matched search_terms:"):
        terms = match_reason.split(":", 1)[1].strip()
        return f"Matches the requested item on {terms}."
    if match_reason.startswith("brand match:"):
        brand = match_reason.split(":", 1)[1].strip()
        return f"Matches on brand ({brand}) and product name."
    if match_reason == "matched on name/description keywords":
        return "Matches closely on the product name and description."
    return "Retrieved as a semantically related option rather than an exact keyword match."


def _family_name(candidate):
    return f"{candidate['brand']} {candidate['subcategory']}"


def _format_candidate(candidate, rank):
    unit_of_measure, unit_of_measure2, pack_ratio = _unit_of_measure(candidate["name"])
    return {
        "product_code": candidate["sku"],
        "description": candidate["name"],
        "brand": _brand_code(candidate["brand"]),
        "quantity": 1,
        "unit_of_measure": unit_of_measure,
        "unit_of_measure2": unit_of_measure2,
        "pack_ratio": pack_ratio,
        "gst_exempt": False,
        "image_url": f"{MOCK_ASSET_HOST}/{candidate['sku']}.jpg",
        "rank": rank,
        "confidence_level": _confidence_level(candidate["confidence"]),
        "rationale": _rationale(candidate["match_reason"]),
        "family_name": _family_name(candidate),
    }


def _build_item_result(item, matched_per_item, extended_per_item):
    query = item["semantic_search_hint"] or item["item_name"]
    candidates = search_products(query, max_results=matched_per_item + extended_per_item)

    formatted = [_format_candidate(c, rank) for rank, c in enumerate(candidates, start=1)]
    for entry in formatted:
        entry["quantity"] = item["quantity"]

    matched = formatted[:matched_per_item]
    alternates = [
        {k: v for k, v in entry.items() if k in ALTERNATE_FIELDS}
        for entry in formatted[matched_per_item : matched_per_item + extended_per_item]
    ]

    status = "not_found" if not matched else CONFIDENCE_LEVEL_TO_STATUS[matched[0]["confidence_level"]]

    return {
        "item_index": item["item_index"],
        "item_name": item["item_name"],
        "spoken_text": item["source_spans"],
        "quantity": item["quantity"],
        "status": status,
        "products": matched,
        "alternates": alternates,
    }


def product_search(query, matched_per_item=DEFAULT_MATCHED_PER_ITEM, extended_per_item=DEFAULT_EXTENDED_PER_ITEM):
    """Extract one or more distinct product requests out of a free-text query
    and search each, returning the real /api/v1/product-search envelope shape:
    per-item status/shortlist/alternates and a human-readable summary.
    """
    t0 = time.perf_counter()
    extracted = extract_items(query)
    truncated_items = 0
    if len(extracted) > MAX_PRODUCT_SEARCH_ITEMS:
        truncated_items = len(extracted) - MAX_PRODUCT_SEARCH_ITEMS
        extracted = extracted[:MAX_PRODUCT_SEARCH_ITEMS]
    extraction_ms = _elapsed_ms(t0)

    t1 = time.perf_counter()
    items = [_build_item_result(item, matched_per_item, extended_per_item) for item in extracted]
    search_ms = _elapsed_ms(t1)

    t2 = time.perf_counter()
    total = sum(len(item["products"]) for item in items)
    summary = (
        f"{total} eligible product option{'s' if total != 1 else ''} shown below in ranked order."
        if total
        else "No eligible product options were found for this query."
    )
    rank_ms = _elapsed_ms(t2)

    return {
        "intent": "product_search",
        "items": items,
        "summary": summary,
        "truncated_items": truncated_items,
        "timings": {
            "extraction_ms": extraction_ms,
            "search_ms": search_ms,
            "rank_ms": rank_ms,
            "total_ms": extraction_ms + search_ms + rank_ms,
        },
    }
