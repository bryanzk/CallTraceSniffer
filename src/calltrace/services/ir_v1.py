"""
Minimal BlockSec -> IR V1 skeleton.
"""
from pathlib import Path
from collections import OrderedDict
from ..utils.ir_format import serialize_ir_payload


def _ordered_swap_node(swap_data, callbacks=None):
    node = OrderedDict()
    node["type"] = "swap"
    node["swap"] = swap_data
    if callbacks:
        node["callback"] = callbacks
    node["transfer"] = None
    return node


def _ordered_transfer_node(transfer_data):
    node = OrderedDict()
    node["type"] = "transfer"
    node["transfer"] = transfer_data
    node["swap"] = None
    return node


def build_ir_skeleton(trace_data):
    """Build a minimal IR skeleton from BlockSec trace_data."""
    data_map = trace_data.get("dataMap", {}) if trace_data else {}
    main_trace = trace_data.get("mainTrace", []) if trace_data else []

    # Minimal swap node based on first swap-like invocation in dataMap.
    swap_id = None
    for node_id, node in data_map.items():
        invocation = node.get("invocation", {})
        method = invocation.get("decodedMethod", {})
        name = method.get("name", "") if isinstance(method, dict) else ""
        if "swap" in name.lower() and "callback" not in name.lower():
            swap_id = node_id
            break

    swap_intent = {
        "poolId": "unknown",
        "protocolId": 3,
        "tokenIn": "unknown",
        "tokenOut": "unknown",
        "tokenInDecimals": None,
        "tokenOutDecimals": None,
        "amountInBig": 0,
        "amountOutBig": 0,
    }
    execution_args = {
        "amount": None,
        "isAmountIn": False,
        "zeroForOne": False,
        "recipient": "",
        "recipientIsBot": False,
        "recipientType": 0,
        "tokenInIsWETH": False,
        "tokenOutIsWETH": False,
    }
    swap_data = {"swapIntent": swap_intent, "executionArgs": execution_args}

    # If no swaps exist, return unknown root.
    if swap_id is None:
        return {
            "tx_hash": trace_data.get("tx_hash", "") if trace_data else "",
            "pattern": "",
            "baseTokenAmountIn": None,
            "baseTokenAmountOut": None,
            "rootTrace": {"type": "unknown", "swap": None, "transfer": None},
        }

    # Minimal callback node (if any child exists in mainTrace)
    callbacks = []
    if main_trace:
        # Only attach a dummy transfer node to validate ordering/empty rules
        transfer_data = {"tokenId": "unknown", "to": "", "amount": 0}
        callbacks.append(_ordered_transfer_node(transfer_data))

    root = _ordered_swap_node(swap_data, callbacks if callbacks else None)

    return {
        "tx_hash": trace_data.get("tx_hash", "") if trace_data else "",
        "pattern": "",
        "baseTokenAmountIn": None,
        "baseTokenAmountOut": None,
        "rootTrace": root,
    }


def write_ir_json(ir_data, output_path):
    """Write IR JSON to a file path."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tx_hash = ir_data.get("tx_hash") if isinstance(ir_data, dict) else None
    path.write_text(serialize_ir_payload(ir_data, tx_hash), encoding="utf-8")
    return str(path)
