"""
Smoke tests for Helin IR case fixtures.
"""
import json
from pathlib import Path


TOP_LEVEL_ORDER = ["pattern", "baseTokenAmountIn", "baseTokenAmountOut", "rootTrace", "children"]
ROOT_TRACE_ORDER = ["type", "swap", "transfer", "wethWrapOrUnwarp", "callback", "encoded"]
SWAP_ORDER = ["swapIntent", "executionArgs"]
SWAP_INTENT_ORDER = [
    "poolId",
    "protocolId",
    "tokenIn",
    "tokenInDecimals",
    "tokenOut",
    "tokenOutDecimals",
    "amountIn",
    "amountInBig",
    "amountInEncoded",
    "amountOut",
    "amountOutBig",
    "amountOutEncoded",
]
EXEC_ARGS_ORDER = [
    "amount",
    "isAmountIn",
    "zeroForOne",
    "recipientIsBot",
    "recipient",
    "recipientType",
    "tokenInIsWETH",
    "tokenOutIsWETH",
]
TRANSFER_ORDER = ["tokenId", "to", "amount"]


def _assert_ordered_subset(actual_keys, expected_order, path):
    positions = []
    for key in expected_order:
        if key in actual_keys:
            positions.append(actual_keys.index(key))
    assert positions == sorted(positions), f"{path} key order mismatch"


def _assert_swap_structure(swap, path):
    assert isinstance(swap, dict), f"{path} expected dict"
    _assert_ordered_subset(list(swap.keys()), SWAP_ORDER, path)
    intent = swap.get("swapIntent", {})
    exec_args = swap.get("executionArgs", {})
    _assert_ordered_subset(list(intent.keys()), SWAP_INTENT_ORDER, f"{path}.swapIntent")
    _assert_ordered_subset(list(exec_args.keys()), EXEC_ARGS_ORDER, f"{path}.executionArgs")


def _assert_trace_node(node, path):
    assert isinstance(node, dict), f"{path} expected dict"
    _assert_ordered_subset(list(node.keys()), ROOT_TRACE_ORDER, path)
    assert node.get("type") in {"swap", "transfer", "unknown"}, f"{path}.type invalid"
    if node.get("swap"):
        _assert_swap_structure(node["swap"], f"{path}.swap")
    if node.get("transfer"):
        _assert_ordered_subset(list(node["transfer"].keys()), TRANSFER_ORDER, f"{path}.transfer")
    for idx, child in enumerate(node.get("callback") or []):
        _assert_trace_node(child, f"{path}.callback[{idx}]")


def test_helin_ir_cases_smoke():
    data = json.loads(Path("tests/fixtures/from helin ir cases.json").read_text())
    assert len(data) == 2
    for tx_hash, ir in data.items():
        assert isinstance(tx_hash, str)
        assert isinstance(ir, dict)
        _assert_ordered_subset(list(ir.keys()), TOP_LEVEL_ORDER, f"{tx_hash}")
        assert "rootTrace" in ir
        assert "children" in ir
        _assert_trace_node(ir["rootTrace"], f"{tx_hash}.rootTrace")
