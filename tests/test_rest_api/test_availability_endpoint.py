def test_availability_endpoint_shape(client, require_live_stack):
    search_resp = client.post("/v1/search_catalogue", json={"query": "basin tap chrome"})
    sku = search_resp.json()["results"][0]["sku"]

    resp = client.get("/v1/availability", params={"sku": sku})
    assert resp.status_code == 200
    data = resp.json()
    assert data["sku"] == sku
    assert len(data["locations"]) == 15


def test_availability_endpoint_unknown_sku_is_404(client):
    resp = client.get("/v1/availability", params={"sku": "NOT-A-REAL-SKU"})
    assert resp.status_code == 404
    assert resp.json()["error"] == "sku_not_found"
