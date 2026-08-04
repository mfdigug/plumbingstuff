from mcp_backend.search import search_products


def test_search_returns_at_most_max_results(golden_queries):
    for case in golden_queries:
        results = search_products(case["query"], max_results=20)
        assert len(results) <= 20


def test_search_hits_expected_category_or_subcategory(golden_queries):
    failures = []
    for case in golden_queries:
        results = search_products(case["query"], max_results=20)
        categories = {r["category"] for r in results}
        subcategories = {r["subcategory"] for r in results}
        expected_categories = set(case.get("expect_any_category", []))
        expected_subcategories = set(case.get("expect_any_subcategory", []))
        hit = bool(expected_categories & categories) or bool(expected_subcategories & subcategories)
        if not hit:
            failures.append(case["query"])
    assert not failures, f"No results matched expectations for queries: {failures}"


def test_confidence_scores_are_normalized():
    results = search_products("basin tap chrome")
    for r in results:
        assert 0.0 <= r["confidence"] <= 1.0


def test_category_filter_is_respected():
    results = search_products("mixer", category="Taps & Mixers")
    assert all(r["category"] == "Taps & Mixers" for r in results)
