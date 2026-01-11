"""
Unit tests for batch routes and IR serialization edge cases.
"""
import io
import json
import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'src'))

flask = pytest.importorskip("flask")
from flask import Flask

from calltrace.api import routes
from calltrace.api.routes import register_routes
from calltrace.services.extractor import BlockSecExtractor


def _valid_hash(ch="a"):
    return "0x" + (ch * 64)


def test_analyze_batch_missing_file():
    app = Flask(__name__)
    cache = {}
    register_routes(app, cache)
    client = app.test_client()
    resp = client.post("/api/analyze-batch")
    assert resp.status_code == 400


def test_analyze_batch_invalid_hash():
    app = Flask(__name__)
    cache = {}
    register_routes(app, cache)
    client = app.test_client()
    data = {"file": (io.BytesIO(b"not-a-hash\n"), "txs.csv")}
    resp = client.post("/api/analyze-batch", data=data, content_type="multipart/form-data")
    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload["results"][0]["success"] is False
    assert "无效的交易哈希格式" in payload["results"][0]["error"]


def test_analyze_batch_success(monkeypatch, sample_trace_data):
    app = Flask(__name__)
    cache = {}
    register_routes(app, cache)

    async def fake_extract(self, tx_hash):
        return {"success": True, "tx_hash": tx_hash, "trace_data": sample_trace_data}

    monkeypatch.setattr(BlockSecExtractor, "extract_blocksec_data", fake_extract)
    client = app.test_client()
    tx_hash = sample_trace_data["tx_hash"]
    data = {"file": (io.BytesIO(f"{tx_hash}\n".encode("utf-8")), "txs.csv")}
    resp = client.post("/api/analyze-batch", data=data, content_type="multipart/form-data")
    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload["results"][0]["success"] is True
    assert "ir_v1_json" in payload["results"][0]


def test_analyze_batch_extractor_failure(monkeypatch):
    app = Flask(__name__)
    cache = {}
    register_routes(app, cache)

    async def fake_extract(self, tx_hash):
        return {"success": False, "tx_hash": tx_hash, "error": "boom"}

    monkeypatch.setattr(BlockSecExtractor, "extract_blocksec_data", fake_extract)
    client = app.test_client()
    tx_hash = _valid_hash("b")
    data = {"file": (io.BytesIO(f"{tx_hash}\n".encode("utf-8")), "txs.csv")}
    resp = client.post("/api/analyze-batch", data=data, content_type="multipart/form-data")
    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload["results"][0]["success"] is False


def test_analyze_simulation_batch_invalid_type():
    app = Flask(__name__)
    cache = {}
    register_routes(app, cache)
    client = app.test_client()
    resp = client.post("/api/analyze-simulation-batch", json={"simulation_urls": "nope"})
    assert resp.status_code == 400


def test_analyze_simulation_batch_over_limit():
    app = Flask(__name__)
    cache = {}
    register_routes(app, cache)
    client = app.test_client()
    urls = [f"https://app.blocksec.com/explorer/tx/eth/{_valid_hash(str(i))}?event=simulation&type=0" for i in range(11)]
    resp = client.post("/api/analyze-simulation-batch", json={"simulation_urls": urls})
    assert resp.status_code == 400


def test_analyze_simulation_batch_success(monkeypatch, sample_trace_data):
    app = Flask(__name__)
    cache = {}
    register_routes(app, cache)

    async def fake_extract(self, sim_url):
        return {"success": True, "tx_hash": sample_trace_data["tx_hash"], "trace_data": sample_trace_data}

    monkeypatch.setattr(BlockSecExtractor, "extract_blocksec_simulation_data", fake_extract)
    client = app.test_client()
    sim_url = f"https://app.blocksec.com/explorer/tx/eth/{sample_trace_data['tx_hash']}?event=simulation&type=0"
    resp = client.post("/api/analyze-simulation-batch", json={"simulation_urls": [sim_url]})
    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload["results"][0]["success"] is True
    assert "ir_v1_json" in payload["results"][0]


def test_download_result_accepts_ir_v1_object():
    app = Flask(__name__)
    cache = {}
    register_routes(app, cache)
    client = app.test_client()
    payload = {"pattern": "", "rootTrace": {"type": "unknown"}, "children": []}
    resp = client.post(
        "/api/download-result",
        json={"tx_hash": _valid_hash("c"), "output_type": "ir_v1", "ir_v1": payload},
    )
    assert resp.status_code == 200
    body = resp.data.decode("utf-8")
    assert "\"pattern\"" in body


def test_serialize_ir_payload_invalid_string_returns_input():
    output = routes._serialize_ir_payload("not-json", "0xabc")
    assert output == "not-json"


def test_serialize_ir_payload_list():
    output = routes._serialize_ir_payload([{"tx_hash": "0xabc", "pattern": ""}], "0xabc")
    parsed = json.loads(output)
    assert isinstance(parsed, list)
    assert parsed[0]["tx_hash"] == "0xabc"
