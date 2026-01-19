import pytest

from flask import Flask

from calltrace.api import routes
from calltrace.api.routes import register_routes
from calltrace.services.dune_service import DuneQueryResult


def _valid_hash(ch="a"):
    return "0x" + (ch * 64)


def test_unipool_check_route(monkeypatch):
    monkeypatch.setenv("DUNE_API_KEY", "test-key")

    class FakeDuneService:
        def __init__(self, *args, **kwargs):
            pass

        def fetch_uniswap_flags(self, tx_hashes):
            return [DuneQueryResult(tx_hash=tx_hashes[0].lower(), bool_used_uni=True)]

    monkeypatch.setattr(routes, "DuneService", FakeDuneService)
    app = Flask(__name__)
    register_routes(app, {})
    client = app.test_client()
    resp = client.post("/api/unipool/check", json={"tx_hashes": [_valid_hash("b")]})
    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload["results"][0]["has_uni_pool"] is True


def test_unipool_status_route(monkeypatch):
    monkeypatch.setenv("DUNE_API_KEY", "test-key")
    monkeypatch.setattr(routes, "DuneService", lambda *args, **kwargs: None)
    app = Flask(__name__)
    register_routes(app, {})
    client = app.test_client()
    resp = client.get("/api/unipool/status")
    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload["pool_count"] == 0
    assert payload["last_sync_time"] is None
    assert payload["storage"] == "disabled"
