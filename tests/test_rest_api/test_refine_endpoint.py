def test_refine_endpoint_narrows_candidates(client, require_live_stack):
    search_resp = client.post("/v1/search", json={"query": "mixer tap"})
    skus = [r["sku"] for r in search_resp.json()["results"]]
    assert skus

    resp = client.post("/v1/refine", json={"candidate_skus": skus, "filters": {"brand": "Definitely Not Real"}})
    assert resp.status_code == 200
    assert resp.json()["results"] == []
