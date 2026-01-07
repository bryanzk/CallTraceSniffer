"""
Mermaid DAG builder tests.
"""
import pytest

from calltrace.services.mermaid_dag import build_mermaid_dag


def test_build_mermaid_dag_basic():
    ir = {
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
                    "amountInBig": 123,
                    "amountOutBig": 456,
                },
                "executionArgs": {
                    "isAmountIn": False,
                    "zeroForOne": False,
                    "recipient": "0xrecipient",
                    "recipientType": 0,
                },
            },
            "callback": [
                {
                    "type": "transfer",
                    "transfer": {
                        "tokenId": "0xtoken",
                        "to": "0xto",
                        "amount": 789,
                    },
                    "callback": [],
                }
            ],
        }
    }

    mermaid = build_mermaid_dag(ir)
    assert "graph TD" in mermaid
    assert "classDef swap" in mermaid
    assert "classDef transfer" in mermaid
    assert "protocolId" in mermaid
    assert "tokenId" in mermaid


def test_build_mermaid_dag_missing_roottrace():
    with pytest.raises(ValueError):
        build_mermaid_dag({})
