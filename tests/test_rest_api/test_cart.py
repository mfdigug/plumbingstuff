CUSTOMER_ID = "CUST-0002"


def test_add_view_remove_cart_flow(client, any_sku):
    add_resp = client.post(f"/v1/cart/{CUSTOMER_ID}/items", json={"sku": any_sku, "quantity": 2})
    assert add_resp.status_code == 200
    cart = add_resp.json()
    assert any(item["sku"] == any_sku and item["quantity"] == 2 for item in cart["items"])

    view_resp = client.get(f"/v1/cart/{CUSTOMER_ID}")
    assert view_resp.status_code == 200
    assert any(item["sku"] == any_sku for item in view_resp.json()["items"])

    remove_resp = client.delete(f"/v1/cart/{CUSTOMER_ID}/items/{any_sku}")
    assert remove_resp.status_code == 200
    assert not any(item["sku"] == any_sku for item in remove_resp.json()["items"])


def test_add_unknown_sku_is_404(client):
    resp = client.post(f"/v1/cart/{CUSTOMER_ID}/items", json={"sku": "NOT-A-REAL-SKU", "quantity": 1})
    assert resp.status_code == 404
    assert resp.json()["error"] == "sku_not_found"


def test_remove_sku_not_in_cart_is_404(client, any_sku):
    resp = client.delete(f"/v1/cart/{CUSTOMER_ID}/items/{any_sku}")
    assert resp.status_code == 404
    assert resp.json()["error"] == "sku_not_in_cart"


def test_cart_for_unknown_customer_is_404(client, any_sku):
    resp = client.get("/v1/cart/CUST-9999")
    assert resp.status_code == 404
    assert resp.json()["error"] == "customer_not_found"
