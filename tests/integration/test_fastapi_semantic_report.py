"""FastAPI semantic report endpoint 测试。"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "api" / "semantic_report_fastapi.py"
FIXTURE = ROOT / "tests" / "fixtures" / "dynamic_semantic_case_92e8.json"


def _load_app():
    spec = importlib.util.spec_from_file_location("semantic_report_fastapi", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod.app


def test_health_endpoint():
    app = _load_app()
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_semantic_report_endpoint_with_local_fixture():
    app = _load_app()
    client = TestClient(app)

    payload = {
        "tx_hash": "0x92e8b6cf1367b5db3810186be30a3148e49283fe33f980919905f0433b1738de",
        "input_json": str(FIXTURE),
        "network_only": False,
        "strict": True,
        "report_style": "default",
        "report_llm": False,
    }
    resp = client.post("/semantic-report", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert "phase_narratives" in body["report"]
    assert "执行摘要" in body["report_markdown"]


def test_semantic_report_network_only_rejects_input_json():
    app = _load_app()
    client = TestClient(app)

    payload = {
        "tx_hash": "0x92e8b6cf1367b5db3810186be30a3148e49283fe33f980919905f0433b1738de",
        "input_json": str(FIXTURE),
        "network_only": True,
    }
    resp = client.post("/semantic-report", json=payload)
    assert resp.status_code == 400
    assert "network_only=true" in resp.json()["detail"]
