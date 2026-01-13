from calltrace.api import routes
from calltrace.app import app, extracted_data_cache
from calltrace.services.blocksec_simulation import SimulationResult


def test_simulate_and_analyze_missing_simulation_id_uses_tx_hash(monkeypatch):
    extracted_data_cache.clear()
    app.testing = True
    tx_hash = "0x" + "a" * 64
    sim_url = (
        "https://app.blocksec.com/explorer/tx/eth/"
        f"{tx_hash}?event=simulation&type=0&timestamp=123"
    )

    def fake_run_simulation(payload):
        return SimulationResult(
            simulation_id=None,
            tx_hash=tx_hash,
            simulation_url=sim_url,
            timestamp_ms=123,
        )

    async def fake_extract(self, url):
        return {
            "success": True,
            "tx_hash": tx_hash,
            "trace_data": {"dataMap": {}, "mainTrace": {}},
        }

    def fake_process_tx_data(trace_data, tx_hash_arg, extra):
        return {"ir_v1": {"rootTrace": None}, "ir_v1_json": "{}", "stats": {}}

    monkeypatch.setattr(routes, "run_simulation", fake_run_simulation)
    monkeypatch.setattr(routes.BlockSecExtractor, "extract_blocksec_simulation_data", fake_extract)
    monkeypatch.setattr(routes, "process_tx_data", fake_process_tx_data)

    client = app.test_client()
    response = client.post(
        "/api/simulate-and-analyze",
        json={
            "sender": "0x1",
            "receiver": "0x2",
            "inputData": "0x",
            "value": "0",
        },
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["tx_hash"] == tx_hash
    assert tx_hash in extracted_data_cache
