"""
Smoke test for BlockSec extra payloads.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'src'))

from calltrace.services.ir_v1_blocksec import build_blocksec_ir


def test_blocksec_extra_payloads_smoke():
    pool = "0x1111111111111111111111111111111111111111"
    token_in = "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    token_out = "0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
    trace_data = {
        "tx_hash": "0xabc",
        "dataMap": {
            "1": {
                "invocation": {
                    "address": pool,
                    "decodedMethod": {"name": "swap", "callParams": []},
                }
            }
        },
        "mainTrace": [{"id": 1, "children": []}],
    }
    extra = {
        "token_info": [
            {"address": token_in, "decimals": 6},
            {"address": token_out, "decimals": 18},
        ],
        "fundflow": [
            {"to": pool, "token": token_in, "amount": "1000"},
            {"from": pool, "token": token_out, "amount": "0.5"},
        ],
        "basic_info": {"callData": "0xdeadbeef"},
    }

    ir = build_blocksec_ir(trace_data, trace_data["tx_hash"], extra)
    assert ir["rootTrace"]["encoded"] == "0xdeadbeef"
