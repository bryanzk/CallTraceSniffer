"""
IR-to-Mermaid API tests.
"""
import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "src"))

flask = pytest.importorskip("flask")
from flask import Flask

from calltrace.api.routes import register_routes


def test_ir_to_mermaid_success():
    app = Flask(__name__)
    cache = {}
    register_routes(app, cache)

    ir = {
        "tx_hash": "0xabc",
        "rootTrace": {
            "type": "swap",
            "swap": {
                "swapIntent": {
                    "poolId": "0xpool",
                    "protocolId": 3,
                    "tokenIn": "0xtokenin",
                    "tokenInDecimals": 6,
                    "tokenOut": "0xtokenout",
                    "tokenOutDecimals": 18,
                    "amountInBig": 1,
                    "amountOutBig": 2,
                },
                "executionArgs": {
                    "isAmountIn": False,
                    "zeroForOne": False,
                    "recipient": "0xrecipient",
                    "recipientType": 0,
                },
            },
            "callback": [],
        },
    }

    client = app.test_client()
    resp = client.post("/api/ir-to-mermaid", json={"ir_v1": ir})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True
    assert "mermaid_dag" in data
    assert "graph TD" in data["mermaid_dag"]


def test_ir_to_mermaid_invalid_payload():
    app = Flask(__name__)
    cache = {}
    register_routes(app, cache)
    client = app.test_client()
    resp = client.post("/api/ir-to-mermaid", json={"ir_v1": "not-json"})
    assert resp.status_code == 400
