"""
Unit tests for API stats helpers (FlowType + gas + IR JSON ordering).
"""
import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'src'))

from calltrace.api import routes
from calltrace.config import config


def _transfer_invocation(from_addr, to_addr, token_addr, amount):
    return {
        "invocation": {
            "address": token_addr,
            "fromAddress": from_addr,
            "decodedMethod": {
                "name": "transfer",
                "callParams": [
                    {"name": "to", "value": to_addr},
                    {"name": "amount", "value": str(amount)},
                ],
            },
        }
    }


def test_compute_flow_counts_with_merge_and_virtual():
    router = list(config.ROUTER_ADDRESSES)[0]
    token = "0x0000000000000000000000000000000000000001"
    trace_data = {
        "dataMap": {
            # A -> Router (transfer)
            "1": _transfer_invocation("0xaaa", router, token, 100),
            # Router -> B (transfer) => should merge into Direct
            "2": _transfer_invocation(router, "0xbbb", token, 100),
            # Direct edge (no router)
            "3": _transfer_invocation("0xccc", "0xddd", token, 200),
            # Virtual edge (from == to)
            "4": _transfer_invocation("0xeee", "0xeee", token, 1),
            # Unmatched router transfer
            "5": _transfer_invocation(router, "0x999", token, 333),
        }
    }

    total, router_count, direct_count, virtual_count = routes._compute_flow_counts(trace_data)
    assert router_count == 1
    assert direct_count == 2  # merged edge + direct edge
    assert virtual_count == 1
    assert total == 4


def test_extract_total_gas_from_gas_flame():
    trace_data = {
        "gasFlame": [
            {
                "name": "Total Gas",
                "children": [
                    {"name": "Actual Gas Used", "value": 12345}
                ],
            }
        ]
    }
    assert routes._extract_total_gas(trace_data) == 12345
    assert routes._extract_total_gas({}) == 0


def test_serialize_ir_payload_orders_tx_hash_first():
    payload = {"pattern": "", "tx_hash": "0xabc", "rootTrace": {"type": "unknown"}}
    output = routes._serialize_ir_payload(payload, "0xabc")
    assert output.lstrip().startswith('{\n  "tx_hash":')
    parsed = json.loads(output)
    assert parsed["tx_hash"] == "0xabc"
