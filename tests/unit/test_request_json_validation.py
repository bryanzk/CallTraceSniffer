from calltrace.app import app


def test_analyze_tx_accepts_missing_json():
    app.testing = True
    client = app.test_client()
    response = client.post("/api/analyze")
    assert response.status_code == 400
    payload = response.get_json()
    assert payload["error"] == "交易哈希不能为空"


def test_analyze_tx_rejects_non_object_json():
    app.testing = True
    client = app.test_client()
    response = client.post("/api/analyze", json=[])
    assert response.status_code == 400
    payload = response.get_json()
    assert payload["error"] == "请求体必须为JSON对象"


def test_analyze_simulation_accepts_missing_json():
    app.testing = True
    client = app.test_client()
    response = client.post("/api/analyze-simulation")
    assert response.status_code == 400
    payload = response.get_json()
    assert payload["error"] == "模拟URL不能为空"


def test_analyze_simulation_rejects_non_object_json():
    app.testing = True
    client = app.test_client()
    response = client.post("/api/analyze-simulation", json=[])
    assert response.status_code == 400
    payload = response.get_json()
    assert payload["error"] == "请求体必须为JSON对象"
