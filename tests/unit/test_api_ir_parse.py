"""
Unit tests for IR parse and download endpoints.
"""
import sys
import os
import json
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'src'))

flask = pytest.importorskip("flask")
from flask import Flask

from calltrace.api.routes import register_routes, process_tx_data
from calltrace.services.extractor import BlockSecExtractor


def test_ir_parse_from_cache(sample_trace_data):
    app = Flask(__name__)
    cache = {}
    register_routes(app, cache)

    analysis = process_tx_data(sample_trace_data, sample_trace_data["tx_hash"])
    cache[sample_trace_data["tx_hash"]] = {"trace_data": sample_trace_data, "analysis": analysis}

    client = app.test_client()
    resp = client.post("/api/ir_parse", json={"tx_hash": sample_trace_data["tx_hash"]})
    assert resp.status_code == 200
    body = resp.data.decode("utf-8")
    assert body.lstrip().startswith('{\n  "tx_hash"')
    payload = json.loads(body)
    assert payload["tx_hash"] == sample_trace_data["tx_hash"]


def test_ir_parse_fetches_when_cache_missing(monkeypatch, sample_trace_data):
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
    resp = client.post("/api/ir_parse", json={"tx_hash": sample_trace_data["tx_hash"]})
    assert resp.status_code == 200
    payload = json.loads(resp.data.decode("utf-8"))
    assert payload["tx_hash"] == sample_trace_data["tx_hash"]


def test_download_result_prefers_provided_json(sample_trace_data):
    app = Flask(__name__)
    cache = {}
    register_routes(app, cache)
    client = app.test_client()

    provided = json.dumps({"tx_hash": sample_trace_data["tx_hash"], "pattern": ""}, indent=2)
    resp = client.post(
        "/api/download-result",
        json={
            "tx_hash": sample_trace_data["tx_hash"],
            "output_type": "ir_v1",
            "ir_v1_json": provided,
        },
    )
    assert resp.status_code == 200
    assert resp.data.decode("utf-8") == provided


def test_download_result_rejects_other_types():
    app = Flask(__name__)
    cache = {}
    register_routes(app, cache)
    client = app.test_client()

    resp = client.post("/api/download-result", json={"tx_hash": "0x123", "output_type": "legacy"})
    assert resp.status_code == 400
