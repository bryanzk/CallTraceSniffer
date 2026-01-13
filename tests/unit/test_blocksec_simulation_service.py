"""
BlockSec simulation service unit tests.
"""
import sys
import os

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'src'))

from calltrace.services import blocksec_simulation


def test_build_simulation_request_payload_txn_custom_keeps_value():
    raw = {
        "chainID": 1,
        "blockNumber": 123,
        "position": 0,
        "txnCustom": {
            "value": "0.1",
            "sender": "0xaaa",
            "receiver": "0xbbb",
            "inputData": "0x1234",
            "gasLimit": 21000,
        },
    }
    payload = blocksec_simulation.build_simulation_request_payload(raw)
    assert payload["txnCustom"]["value"] == "0.1"
    assert payload["chainID"] == 1
    assert payload["simulationType"] == "custom"


def test_build_simulation_request_payload_flat_converts_eth():
    raw = {
        "sender": "0xaaa",
        "receiver": "0xbbb",
        "inputData": "0x1234",
        "value": "0.000000000258280864",
        "gasLimit": 21000,
    }
    payload = blocksec_simulation.build_simulation_request_payload(raw)
    assert payload["value"] == "258280864"
    assert payload["chainID"] == 1


def test_build_simulation_request_payload_flat_no_convert():
    raw = {
        "sender": "0xaaa",
        "receiver": "0xbbb",
        "inputData": "0x1234",
        "value": "258280864",
        "gasLimit": 21000,
    }
    payload = blocksec_simulation.build_simulation_request_payload(raw, convert_value_for_flat=False)
    assert payload["value"] == "258280864"


def test_run_simulation_with_payload_without_simulation_id(monkeypatch):
    def fake_post(session, url, payload):
        return {"hash": "0x" + "1" * 64, "chainID": 1}

    def fake_session(cookie_file=None):
        return object()

    monkeypatch.setattr(blocksec_simulation, "post_blocksec_api", fake_post)
    monkeypatch.setattr(blocksec_simulation, "build_blocksec_session", fake_session)

    payload = {"chainID": 1, "chain": "eth", "from": "0xaaa", "to": "0xbbb", "data": "0x", "value": "0"}
    result = blocksec_simulation.run_simulation_with_payload(payload, fetch_trace=True)

    assert result.simulation_id is None
    assert result.tx_hash.startswith("0x")
    assert "event=simulation" in result.simulation_url
