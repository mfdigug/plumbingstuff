def test_search_mode_shape(client, require_live_stack):
    resp = client.post("/v1/search_catalogue", json={"query": "basin tap chrome"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["query"] == "basin tap chrome"
    assert data["result_count"] == len(data["results"])
    if data["results"]:
        first = data["results"][0]
        assert {"sku", "name", "brand", "confidence", "match_reason"} <= first.keys()


def test_refine_mode_narrows_candidates(client, require_live_stack):
    search_resp = client.post("/v1/search_catalogue", json={"query": "mixer tap"})
    skus = [r["sku"] for r in search_resp.json()["results"]]
    assert skus

    resp = client.post(
        "/v1/search_catalogue",
        json={"candidate_skus": skus, "filters": {"brand": "Definitely Not Real"}},
    )
    assert resp.status_code == 200
    assert resp.json()["results"] == []


def test_neither_query_nor_candidates_is_422(client):
    resp = client.post("/v1/search_catalogue", json={})
    assert resp.status_code == 422
