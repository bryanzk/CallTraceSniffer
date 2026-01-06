"""
Unit tests for IR V1 skeleton output ordering and structure.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'src'))

from calltrace.services.ir_v1 import build_ir_skeleton, write_ir_json


def test_ir_skeleton_ordering_minimal():
    trace_data = {
        "tx_hash": "0x123",
        "dataMap": {
            "1": {"invocation": {"decodedMethod": {"name": "swap"}}}
        },
        "mainTrace": []
    }

    ir = build_ir_skeleton(trace_data)
    root = ir["rootTrace"]

    assert list(root.keys()) == ["type", "swap", "transfer"]
    assert root["type"] == "swap"
    assert root["swap"] is not None
    assert root["transfer"] is None
    assert "callback" not in root


def test_ir_skeleton_with_callback_ordering():
    trace_data = {
        "tx_hash": "0x123",
        "dataMap": {
            "1": {"invocation": {"decodedMethod": {"name": "swap"}}}
        },
        "mainTrace": [{"id": 1, "children": []}]
    }

    ir = build_ir_skeleton(trace_data)
    root = ir["rootTrace"]

    assert list(root.keys()) == ["type", "swap", "callback", "transfer"]
    assert root["type"] == "swap"
    assert isinstance(root["callback"], list)
    assert len(root["callback"]) == 1
    child = root["callback"][0]
    assert list(child.keys()) == ["type", "transfer", "swap"]


def test_ir_skeleton_unknown_when_no_swaps(tmp_path):
    ir = build_ir_skeleton({"tx_hash": "0x123", "dataMap": {}, "mainTrace": []})
    assert ir["rootTrace"]["type"] == "unknown"

    output_path = tmp_path / "ir.json"
    written = write_ir_json(ir, output_path)
    assert os.path.exists(written)
