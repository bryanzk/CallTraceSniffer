"""
模拟交易API与URL解析测试
"""
import sys
import os
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'src'))

flask = pytest.importorskip("flask")
from flask import Flask
from calltrace.api.routes import register_routes
from calltrace.services.extractor import BlockSecExtractor


def test_parse_simulation_url_success():
    url = "https://app.blocksec.com/explorer/tx/eth/0x0807fd45ea0116616ab5cb6b81dd1c395179713fd2465c1d610df14c0c404004?event=simulation&type=0"
    tx_hash, normalized = BlockSecExtractor.parse_simulation_url(url)
    assert tx_hash == "0x0807fd45ea0116616ab5cb6b81dd1c395179713fd2465c1d610df14c0c404004"
    assert normalized == url


def test_parse_simulation_url_invalid():
    try:
        BlockSecExtractor.parse_simulation_url("https://example.com/")
    except ValueError as exc:
        assert "BlockSec" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


def test_analyze_simulation_route_success(monkeypatch, sample_trace_data):
    app = Flask(__name__)
    cache = {}
    register_routes(app, cache)

    async def fake_extract(self, sim_url):
        return {
            "success": True,
            "tx_hash": sample_trace_data["tx_hash"],
            "trace_data": sample_trace_data,
        }

    monkeypatch.setattr(BlockSecExtractor, "extract_blocksec_simulation_data", fake_extract)

    client = app.test_client()
    resp = client.post(
        "/api/analyze-simulation",
        json={
            "simulation_url": f"https://app.blocksec.com/explorer/tx/eth/{sample_trace_data['tx_hash']}?event=simulation&type=0"
        },
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True
    assert data["tx_hash"] == sample_trace_data["tx_hash"]
    assert "ir_v1_json" in data
    assert "mermaid_dag" in data


def test_analyze_simulation_route_invalid_url():
    app = Flask(__name__)
    cache = {}
    register_routes(app, cache)
    client = app.test_client()
    resp = client.post("/api/analyze-simulation", json={"simulation_url": "not-a-url"})
    assert resp.status_code == 400
