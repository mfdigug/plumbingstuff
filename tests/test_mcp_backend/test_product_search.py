from mcp_backend.search import product_search


def test_multi_item_query_produces_one_result_group_per_item():
    result = product_search("a 90mm stormwater flex and a roll of PTFE tape")
    assert len(result["extraction"]["items"]) == 2
    assert len(result["items"]) == 2
    assert result["items"][0]["item_name"] == "90mm stormwater flex"
    assert result["items"][1]["item_name"] == "PTFE tape"


def test_matched_products_are_capped_and_extended_candidates_follow():
    result = product_search("basin tap chrome", matched_per_item=2, extended_per_item=3)
    item = result["items"][0]
    assert len(item["products"]) <= 2
    assert len(item["extended_candidates"]) <= 3


def test_extended_candidates_omit_fusion_only_fields():
    result = product_search("basin tap chrome", matched_per_item=1, extended_per_item=3)
    item = result["items"][0]
    for candidate in item["extended_candidates"]:
        assert "found_by" not in candidate
        assert "fused_score" not in candidate
        assert "quantity" not in candidate


def test_top_level_products_is_flattened_matched_list():
    result = product_search("toilet suite, basin mixer", matched_per_item=2)
    flattened = [p for item in result["items"] for p in item["products"]]
    assert result["products"] == flattened


def test_summary_reflects_total_matched_count():
    result = product_search("basin tap chrome", matched_per_item=2)
    total = len(result["products"])
    if total:
        assert str(total) in result["summary"]
    else:
        assert "No eligible" in result["summary"]


def test_timings_are_present_and_nonnegative():
    result = product_search("basin tap chrome")
    timings = result["timings"]
    assert timings["total_ms"] == timings["extraction_ms"] + timings["search_ms"] + timings["rank_ms"]
    assert all(v >= 0 for v in timings.values())


def test_no_match_status_when_query_has_no_hits():
    result = product_search("zzz-totally-nonexistent-product-zzz")
    assert result["items"][0]["status"] == "no_match"
    assert result["items"][0]["products"] == []
