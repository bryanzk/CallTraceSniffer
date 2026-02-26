from __future__ import annotations

from typing import Any

import pytest

from calltrace.services.blocksec_adapter import (
    fetch_payload_via_api,
    get_playwright_extractor_class,
    parse_tx,
    parse_simulation_url_tuple,
    sanitize_payload,
)


def test_blocksec_adapter_loads_external_extractor_class():
    cls = get_playwright_extractor_class()
    assert hasattr(cls, "extract_blocksec_data")
    assert hasattr(cls, "extract_blocksec_simulation_data")


def test_blocksec_adapter_parse_simulation_url_tuple():
    tx = "0x" + ("1" * 64)
    url = f"https://app.blocksec.com/explorer/tx/eth/{tx}?event=simulation&type=0"
    parsed_tx, normalized = parse_simulation_url_tuple(url)
    assert parsed_tx == tx
    assert normalized == url


def test_blocksec_adapter_sanitize_payload():
    raw = {
        "success": True,
        "tx_hash": "0x" + ("1" * 64),
        "trace_data": {"dataMap": {}, "mainTrace": []},
    }
    clean = sanitize_payload(raw)
    assert "trace_data" in clean
    assert "success" not in clean


class _DummyResponse:
    def __init__(self, status_code: int, payload: dict[str, Any] | None = None, text: str = "") -> None:
        self.status_code = status_code
        self._payload = payload
        self.text = text

    def json(self) -> dict[str, Any]:
        if self._payload is None:
            raise ValueError("not json")
        return self._payload


def test_parse_tx_calls_remote_api(monkeypatch: pytest.MonkeyPatch):
    captured: dict[str, Any] = {}

    def fake_post(url, json=None, headers=None, timeout=0):  # noqa: A002
        captured["url"] = url
        captured["json"] = json
        captured["headers"] = headers
        captured["timeout"] = timeout
        return _DummyResponse(
            200,
            {
                "success": True,
                "tx_hash": json["tx_hash"],
                "strategy_used": "api",
                "raw": {},
                "clean": {"trace_data": {"dataMap": {}, "mainTrace": []}},
                "error": None,
                "meta": {"duration_ms": 1, "retries": 0, "timestamp": 1},
            },
        )

    monkeypatch.setenv("BLOCKSEC_PARSER_API_BASE_URL", "http://test-host:4444")
    monkeypatch.setattr("calltrace.services.blocksec_adapter.requests.post", fake_post)

    tx_hash = "0x" + ("1" * 64)
    result = parse_tx(tx_hash, strategy="api")
    assert result["success"] is True
    assert captured["url"] == "http://test-host:4444/v1/parse/tx"
    assert captured["json"] == {"tx_hash": tx_hash, "strategy": "api"}
    assert captured["headers"]["Content-Type"] == "application/json"


def test_parse_tx_invalid_payload_returns_value_error(monkeypatch: pytest.MonkeyPatch):
    def fake_post(url, json=None, headers=None, timeout=0):  # noqa: A002
        return _DummyResponse(422, text="invalid tx_hash")

    monkeypatch.setattr("calltrace.services.blocksec_adapter.requests.post", fake_post)

    with pytest.raises(ValueError):
        parse_tx("0x" + ("1" * 64))


def test_fetch_payload_via_api_returns_clean_or_raise(monkeypatch: pytest.MonkeyPatch):
    def fake_post_ok(url, json=None, headers=None, timeout=0):  # noqa: A002
        return _DummyResponse(
            200,
            {
                "success": True,
                "tx_hash": json["tx_hash"],
                "strategy_used": "api",
                "raw": {"trace_data": {"dataMap": {}, "mainTrace": []}},
                "clean": {"trace_data": {"dataMap": {}, "mainTrace": []}, "fundflow": []},
                "error": None,
                "meta": {"duration_ms": 2, "retries": 0, "timestamp": 2},
            },
        )

    monkeypatch.setattr("calltrace.services.blocksec_adapter.requests.post", fake_post_ok)
    clean = fetch_payload_via_api("0x" + ("2" * 64))
    assert clean["trace_data"]["mainTrace"] == []

    def fake_post_bad(url, json=None, headers=None, timeout=0):  # noqa: A002
        return _DummyResponse(
            200,
            {
                "success": False,
                "tx_hash": json["tx_hash"],
                "strategy_used": "api",
                "raw": {},
                "clean": {},
                "error": "upstream failed",
                "meta": {"duration_ms": 3, "retries": 0, "timestamp": 3},
            },
        )

    monkeypatch.setattr("calltrace.services.blocksec_adapter.requests.post", fake_post_bad)
    with pytest.raises(RuntimeError):
        fetch_payload_via_api("0x" + ("3" * 64))


def test_parse_tx_retries_on_502_then_success(monkeypatch: pytest.MonkeyPatch):
    calls = {"count": 0}

    def fake_post(url, json=None, headers=None, timeout=0):  # noqa: A002
        calls["count"] += 1
        if calls["count"] < 2:
            return _DummyResponse(502, text="bad gateway")
        return _DummyResponse(
            200,
            {
                "success": True,
                "tx_hash": json["tx_hash"],
                "strategy_used": "api",
                "raw": {},
                "clean": {"trace_data": {"dataMap": {}, "mainTrace": []}},
                "error": None,
                "meta": {"duration_ms": 1, "retries": 1, "timestamp": 1},
            },
        )

    monkeypatch.setattr("calltrace.services.blocksec_adapter.requests.post", fake_post)
    monkeypatch.setattr("calltrace.services.blocksec_adapter.time.sleep", lambda _n: None)

    result = parse_tx("0x" + ("4" * 64), strategy="api")
    assert result["success"] is True
    assert calls["count"] == 2
