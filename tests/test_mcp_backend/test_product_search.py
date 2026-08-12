from mcp_backend.search import product_search

VALID_STATUSES = {"matched", "needs_checking", "not_found"}
ALTERNATE_ONLY_FIELDS = ("rank", "confidence_level", "rationale", "family_name", "brand", "quantity")


def test_multi_item_query_produces_one_result_group_per_item():
    result = product_search("a 90mm stormwater flex and a roll of PTFE tape")
    assert len(result["items"]) == 2
    assert result["items"][0]["item_name"] == "90mm stormwater flex"
    assert result["items"][1]["item_name"] == "PTFE tape"


def test_matched_products_are_capped_and_alternates_follow():
    result = product_search("basin tap chrome", matched_per_item=2, extended_per_item=3)
    item = result["items"][0]
    assert len(item["products"]) <= 2
    assert len(item["alternates"]) <= 3


def test_alternates_carry_no_ranking_verdict():
    result = product_search("basin tap chrome", matched_per_item=1, extended_per_item=3)
    item = result["items"][0]
    for candidate in item["alternates"]:
        for field in ALTERNATE_ONLY_FIELDS:
            assert field not in candidate


def test_matched_products_carry_rank_confidence_and_rationale():
    result = product_search("basin tap chrome", matched_per_item=2)
    for product in result["items"][0]["products"]:
        assert product["rank"] >= 1
        assert product["confidence_level"] in ("high", "medium", "low")
        assert product["rationale"]
        assert product["family_name"]


def test_status_is_always_one_of_the_three_contract_values():
    for query in ["basin tap chrome", "need an elbow", "zzz-totally-nonexistent-product-zzz"]:
        result = product_search(query)
        for item in result["items"]:
            assert item["status"] in VALID_STATUSES


def test_summary_reflects_total_matched_count():
    result = product_search("basin tap chrome", matched_per_item=2)
    total = sum(len(item["products"]) for item in result["items"])
    if total:
        assert str(total) in result["summary"]
    else:
        assert "No eligible" in result["summary"]


def test_timings_are_present_and_nonnegative():
    result = product_search("basin tap chrome")
    timings = result["timings"]
    assert timings["total_ms"] == timings["extraction_ms"] + timings["search_ms"] + timings["rank_ms"]
    assert all(v >= 0 for v in timings.values())


def test_not_found_status_when_query_has_no_hits():
    result = product_search("zzz-totally-nonexistent-product-zzz")
    assert result["items"][0]["status"] == "not_found"
    assert result["items"][0]["products"] == []
