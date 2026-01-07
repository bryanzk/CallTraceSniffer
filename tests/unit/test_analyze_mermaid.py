"""
Analyze API Mermaid DAG output tests.
"""
import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "src"))

flask = pytest.importorskip("flask")
from flask import Flask

from calltrace.api.routes import register_routes
from calltrace.services.extractor import BlockSecExtractor


def test_analyze_tx_includes_mermaid(monkeypatch, sample_trace_data):
    app = Flask(__name__)
    cache = {}
    register_routes(app, cache)

    async def fake_extract(self, tx_hash):
        return {
            "success": True,
            "tx_hash": sample_trace_data["tx_hash"],
            "trace_data": sample_trace_data,
        }

    monkeypatch.setattr(BlockSecExtractor, "extract_blocksec_data", fake_extract)

    client = app.test_client()
    resp = client.post("/api/analyze", json={"tx_hash": sample_trace_data["tx_hash"]})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True
    assert "mermaid_dag" in data
    assert "graph TD" in data["mermaid_dag"]
