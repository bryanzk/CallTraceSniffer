"""
Unit tests for API stats helpers (FlowType + gas + IR JSON ordering).
"""
import sys
import os
import json
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'src'))

pytest.importorskip("flask")
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


def test_serialize_ir_payload_orders_root_trace_keys():
    payload = {
        "children": [],
        "rootTrace": {
            "callback": [],
            "transfer": None,
            "swap": {},
            "encoded": "0x",
            "wethWrapOrUnwarp": None,
            "type": "swap",
        },
        "baseTokenAmountOut": 1,
        "pattern": "",
        "baseTokenAmountIn": 2,
    }
    output = routes._serialize_ir_payload(payload, "0xabc")
    parsed = json.loads(output)
    assert list(parsed.keys()) == [
        "tx_hash",
        "pattern",
        "baseTokenAmountIn",
        "baseTokenAmountOut",
        "rootTrace",
        "children",
    ]
    assert list(parsed["rootTrace"].keys()) == [
        "type",
        "swap",
        "transfer",
        "wethWrapOrUnwarp",
        "callback",
        "encoded",
    ]


def test_count_ir_nodes_nested():
    root = {
        "type": "swap",
        "swap": {},
        "transfer": None,
        "callback": [
            {"type": "transfer", "swap": None, "transfer": {}},
            {
                "type": "swap",
                "swap": {},
                "transfer": None,
                "callback": [{"type": "transfer", "swap": None, "transfer": {}}],
            },
        ],
    }
    swaps, transfers = routes._count_ir_nodes(root)
    assert swaps == 2
    assert transfers == 2


def test_extract_transfer_edges_filters_and_normalizes():
    trace_data = {
        "dataMap": {
            "1": _transfer_invocation("0xAAA", "0xBBB", "0xToken", 123),
            "2": {
                "invocation": {
                    "address": "0xOther",
                    "decodedMethod": {"name": "swap", "callParams": []},
                }
            },
        }
    }
    edges = routes._extract_transfer_edges(trace_data)
    assert len(edges) == 1
    edge = edges[0]
    assert edge["from"] == "0xaaa"
    assert edge["to"] == "0xbbb"
    assert edge["token"] == "0xtoken"
    assert edge["amount"] == 123
