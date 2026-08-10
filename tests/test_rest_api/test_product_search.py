def test_product_search_shape(client, require_live_stack):
    resp = client.post(
        "/api/v1/product-search",
        json={"query": "I need a 90mm stormwater flex and a roll of PTFE tape", "region": "AU", "branchId": "1234"},
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["intent"] == "product_search"
    assert "requestId" in data

    extraction = data["extraction"]
    assert [item["itemName"] for item in extraction["items"]] == ["90mm stormwater flex", "PTFE tape"]
    assert extraction["items"][0]["sourceSpans"] == ["90mm stormwater flex"]
    assert extraction["items"][1]["sourceSpans"] == ["a roll of PTFE tape"]

    assert len(data["items"]) == 2
    first_item = data["items"][0]
    assert first_item["itemIndex"] == 0
    assert first_item["status"] in ("matched", "no_match")
    for product in first_item["products"]:
        # Always present regardless of which retrieval path produced the hit.
        assert {
            "productCode", "description", "searchScore", "source", "confidence",
            "foundBy", "foundByBoth", "topRankAgreement", "fusedScore", "quantity",
        } <= product.keys()
        if product["source"] == "elasticsearch":
            assert {"brand", "esSalesRank", "esRelevanceScore", "esRelevanceNormalized", "esQueryStrategy", "sourceRank"} <= product.keys()
        elif product["source"] == "mcp":
            assert "country" in product
            assert "esSalesRank" not in product

    assert data["products"] == [p for item in data["items"] for p in item["products"]]
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
