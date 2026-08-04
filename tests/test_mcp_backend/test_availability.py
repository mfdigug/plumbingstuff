from mcp_backend.availability import check_availability
from mcp_backend.search import search_products

VALID_STATUSES = {"in_stock", "out_of_stock", "special_order", "not_carried"}


def _any_sku():
    results = search_products("basin tap chrome")
    assert results, "search_products returned no candidates"
    return results[0]["sku"]


def test_availability_covers_all_15_stores_by_default():
    locations = check_availability(_any_sku())
    assert len(locations) == 15


def test_availability_statuses_are_valid():
    locations = check_availability(_any_sku())
    assert {loc["status"] for loc in locations} <= VALID_STATUSES


def test_availability_filters_by_state():
    locations = check_availability(_any_sku(), state="NSW")
    assert locations
    assert all(loc["state"] == "NSW" for loc in locations)


def test_availability_no_doc_synthesizes_not_carried_not_omitted():
    sku = _any_sku()
    all_stores_result = check_availability(sku)
    not_carried = [loc for loc in all_stores_result if loc["status"] == "not_carried"]
    for loc in not_carried:
        assert loc["qty_on_hand"] == 0
        assert loc["eta_days"] is None
