def test_search_single_item_shape(client, require_live_stack):
    resp = client.post("/v1/search_catalogue", json={"items": ["basin tap chrome"]})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["results"]) == 1
    group = data["results"][0]
    assert group["query"] == "basin tap chrome"
    assert group["match_count"] == len(group["matches"])
    assert group["match_count"] <= 4  # default max_results_per_item
    if group["matches"]:
        first = group["matches"][0]
        assert {"sku", "name", "brand", "confidence", "match_reason"} <= first.keys()


def test_search_multiple_items(client, require_live_stack):
    resp = client.post("/v1/search_catalogue", json={"items": ["toilet suite", "basin mixer"]})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["results"]) == 2
    assert data["results"][0]["query"] == "toilet suite"
    assert data["results"][1]["query"] == "basin mixer"


def test_max_results_per_item_is_respected(client, require_live_stack):
    resp = client.post(
        "/v1/search_catalogue", json={"items": ["mixer tap"], "max_results_per_item": 2}
    )
    assert resp.status_code == 200
    assert len(resp.json()["results"][0]["matches"]) <= 2


def test_missing_items_is_422(client):
    resp = client.post("/v1/search_catalogue", json={})
    assert resp.status_code == 422


def test_empty_items_array_is_422(client):
    resp = client.post("/v1/search_catalogue", json={"items": []})
    assert resp.status_code == 422
