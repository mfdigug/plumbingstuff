def test_get_known_customer_profile(client):
    resp = client.get("/v1/customers/CUST-0001")
    assert resp.status_code == 200
    data = resp.json()
    assert data["customer_id"] == "CUST-0001"
    assert "email" in data and "preferred_store_id" in data


def test_get_unknown_customer_is_404(client):
    resp = client.get("/v1/customers/CUST-9999")
    assert resp.status_code == 404
    assert resp.json()["error"] == "customer_not_found"
