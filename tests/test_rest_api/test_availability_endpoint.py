def test_availability_endpoint_shape(client, require_live_stack, any_sku):
    resp = client.get("/v1/availability", params={"sku": any_sku})
    assert resp.status_code == 200
    data = resp.json()
    assert data["sku"] == any_sku
    assert len(data["locations"]) == 15


def test_availability_endpoint_unknown_sku_is_404(client):
    resp = client.get("/v1/availability", params={"sku": "NOT-A-REAL-SKU"})
    assert resp.status_code == 404
    assert resp.json()["error"] == "sku_not_found"
