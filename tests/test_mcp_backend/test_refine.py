from mcp_backend.refine import refine_candidates
from mcp_backend.search import search_products


def test_refine_narrows_by_brand():
    results = search_products("mixer tap")
    skus = [r["sku"] for r in results]
    assert skus, "search_products returned no candidates to refine"
    brand = results[0]["brand"]

    refined = refine_candidates(skus, {"brand": brand})
    assert refined
    assert all(r["brand"] == brand for r in refined)


def test_refine_returns_empty_list_when_filters_eliminate_all_candidates():
    results = search_products("mixer tap")
    skus = [r["sku"] for r in results]

    refined = refine_candidates(skus, {"brand": "Definitely Not A Real Brand"})
    assert refined == []
