from calltrace.app import app


def test_mev_block_requires_block_number():
    app.testing = True
    client = app.test_client()
    response = client.post("/api/mev/block", json={})
    assert response.status_code == 400
    payload = response.get_json()
    assert payload["error"] == "区块号不能为空"


def test_mev_block_rejects_invalid_block_number():
    app.testing = True
    client = app.test_client()
    response = client.post("/api/mev/block", json={"block_number": "abc"})
    assert response.status_code == 400
    payload = response.get_json()
    assert payload["error"] == "区块号必须为正整数"
