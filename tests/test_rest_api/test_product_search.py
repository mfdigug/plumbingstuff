def test_product_search_shape(client, require_live_stack):
    resp = client.post(
        "/api/v1/product-search",
        json={"query": "I need a 90mm stormwater flex and a roll of PTFE tape", "region": "AU", "branchId": "1234"},
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["intent"] == "product_search"
    assert "requestId" in data

    assert len(data["items"]) == 2
    assert [item["itemName"] for item in data["items"]] == ["90mm stormwater flex", "PTFE tape"]
    assert data["items"][0]["spokenText"] == ["90mm stormwater flex"]
    assert data["items"][1]["spokenText"] == ["a roll of PTFE tape"]

    first_item = data["items"][0]
    assert first_item["itemIndex"] == 0
    assert first_item["status"] in ("matched", "needs_checking", "not_found")
    for product in first_item["products"]:
        # Every shortlisted product carries a ranking verdict; no numeric score anywhere.
        assert {"productCode", "description", "quantity", "rank", "confidenceLevel", "rationale"} <= product.keys()
        assert product["confidenceLevel"] in ("high", "medium", "low")
        assert "confidence" not in product
        assert "searchScore" not in product
    for alternate in first_item["alternates"]:
        # Alternates are catalogue display facts only -- no ranking verdict.
        assert {"rank", "confidenceLevel", "rationale", "familyName"}.isdisjoint(alternate.keys())

    assert "extraction" not in data
    assert "products" not in data
    assert "extractionMs" in data["timings"]
    assert isinstance(data["truncatedItems"], int)


def test_product_search_single_item_query(client, require_live_stack):
    resp = client.post("/api/v1/product-search", json={"query": "basin tap chrome", "region": "AU", "branchId": "1234"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 1


def test_product_search_requires_query(client):
    resp = client.post("/api/v1/product-search", json={"region": "AU", "branchId": "1234"})
    assert resp.status_code == 422


def test_product_search_empty_query_is_422(client):
    resp = client.post("/api/v1/product-search", json={"query": "", "region": "AU", "branchId": "1234"})
    assert resp.status_code == 422


def test_product_search_region_and_branch_id_are_optional(client, require_live_stack):
    resp = client.post("/api/v1/product-search", json={"query": "basin tap chrome"})
    assert resp.status_code == 200
