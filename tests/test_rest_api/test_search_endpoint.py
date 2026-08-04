def test_search_endpoint_shape(client, require_live_stack):
    resp = client.post("/v1/search", json={"query": "basin tap chrome"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["query"] == "basin tap chrome"
    assert data["result_count"] == len(data["results"])
    if data["results"]:
        first = data["results"][0]
        assert {"sku", "name", "brand", "confidence", "match_reason"} <= first.keys()


def test_search_endpoint_validation_error(client):
    resp = client.post("/v1/search", json={})
    assert resp.status_code == 422
