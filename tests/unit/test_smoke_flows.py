"""
Smoke coverage for core API flows.
"""
import sys
import os

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'src'))

from flask import Flask

from calltrace.api import routes
from calltrace.services.blocksec_simulation import SimulationResult
from calltrace.services.extractor import BlockSecExtractor


def _make_app():
    app = Flask(__name__)
    routes.register_routes(app, {})
    return app


@pytest.mark.smoke
def test_smoke_analyze_single_tx(monkeypatch, sample_trace_data):
    async def fake_extract(self, tx_hash):
        return {
            "success": True,
            "tx_hash": tx_hash,
            "trace_data": sample_trace_data,
        }

    monkeypatch.setattr(BlockSecExtractor, "extract_blocksec_data", fake_extract)

    client = _make_app().test_client()
    resp = client.post("/api/analyze", json={"tx_hash": sample_trace_data["tx_hash"]})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True
    assert "ir_v1_json" in data


@pytest.mark.smoke
def test_smoke_analyze_simulation_url(monkeypatch, sample_trace_data):
    async def fake_extract(self, sim_url):
        return {
            "success": True,
            "tx_hash": sample_trace_data["tx_hash"],
            "trace_data": sample_trace_data,
        }

    monkeypatch.setattr(BlockSecExtractor, "extract_blocksec_simulation_data", fake_extract)

    client = _make_app().test_client()
    sim_url = f"https://app.blocksec.com/explorer/tx/eth/{sample_trace_data['tx_hash']}?event=simulation&type=0"
    resp = client.post("/api/analyze-simulation", json={"simulation_url": sim_url})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True
    assert "ir_v1_json" in data


@pytest.mark.smoke
def test_smoke_simulate_and_analyze(monkeypatch, sample_trace_data):
    def fake_run_simulation_with_payload(payload):
        return SimulationResult(
            simulation_id="sim-1",
            tx_hash=sample_trace_data["tx_hash"],
            simulation_url=f"https://app.blocksec.com/explorer/tx/eth/{sample_trace_data['tx_hash']}?event=simulation",
            timestamp_ms=1234567890,
            trace_data=sample_trace_data,
            balance_change={"changes": []},
            basic_info={"callData": "0x"},
        )

    monkeypatch.setattr(routes, "run_simulation_with_payload", fake_run_simulation_with_payload)

    client = _make_app().test_client()
    resp = client.post(
        "/api/simulate-and-analyze",
        json={"params": {"sender": "0xaaa", "receiver": "0xbbb", "inputData": "0x", "value": "0.1", "gasLimit": 21000}},
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True
    assert data["simulation_url"].startswith("https://app.blocksec.com/explorer/tx/eth/")
