"""
BlockSec IR V1 mapping for blocksec IF example.
"""
import json
import math
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'src'))

from calltrace.services.ir_v1_blocksec import build_blocksec_ir


TX_HASH = "0x34d13a12d4a860ee931cbfafcc016825eeabcec64e82b09c54da7646f8c85b15"
TOP_LEVEL_ORDER = ['tx_hash', 'pattern', 'baseTokenAmountIn', 'baseTokenAmountOut', 'rootTrace', 'children']
ROOT_TRACE_ORDER = ['type', 'swap', 'transfer', 'wethWrapOrUnwarp', 'callback', 'encoded']
SWAP_ORDER = ['swapIntent', 'executionArgs']
SWAP_INTENT_ORDER = [
    'poolId',
    'protocolId',
    'tokenIn',
    'tokenInDecimals',
    'tokenOut',
    'tokenOutDecimals',
    'amountIn',
    'amountInBig',
    'amountInEncoded',
    'amountOut',
    'amountOutBig',
    'amountOutEncoded',
]
EXEC_ARGS_ORDER = [
    'amount',
    'isAmountIn',
    'zeroForOne',
    'recipientIsBot',
    'recipient',
    'recipientType',
    'tokenInIsWETH',
    'tokenOutIsWETH',
]
TRANSFER_ORDER = ['tokenId', 'to', 'amount']


def _ordered_by_keys(data, key_order):
    ordered = {}
    for key in key_order:
        if key in data:
            ordered[key] = data[key]
    for key in data:
        if key not in ordered:
            ordered[key] = data[key]
    return ordered


def _order_ir_value(value):
    if isinstance(value, dict):
        return _order_ir_dict(value)
    if isinstance(value, list):
        return [_order_ir_value(item) for item in value]
    return value


def _order_ir_dict(data):
    processed = {key: _order_ir_value(value) for key, value in data.items()}

    if 'rootTrace' in processed and 'children' in processed:
        return _ordered_by_keys(processed, TOP_LEVEL_ORDER)

    if 'swapIntent' in processed or 'executionArgs' in processed:
        ordered = _ordered_by_keys(processed, SWAP_ORDER)
        if 'swapIntent' in ordered and isinstance(ordered.get('swapIntent'), dict):
            ordered['swapIntent'] = _ordered_by_keys(ordered['swapIntent'], SWAP_INTENT_ORDER)
        if 'executionArgs' in ordered and isinstance(ordered.get('executionArgs'), dict):
            ordered['executionArgs'] = _ordered_by_keys(ordered['executionArgs'], EXEC_ARGS_ORDER)
        return ordered

    if 'poolId' in processed and 'protocolId' in processed and ('tokenIn' in processed or 'tokenOut' in processed):
        return _ordered_by_keys(processed, SWAP_INTENT_ORDER)

    if 'type' in processed and ('swap' in processed or 'transfer' in processed):
        return _ordered_by_keys(processed, ROOT_TRACE_ORDER)

    if set(TRANSFER_ORDER).issubset(processed.keys()):
        return _ordered_by_keys(processed, TRANSFER_ORDER)

    return processed


def _assert_ir_equal(actual, expected, path=""):
    if isinstance(expected, dict):
        assert isinstance(actual, dict), f"{path} expected dict"
        assert list(actual.keys()) == list(expected.keys()), f"{path} key order mismatch"
        for key, exp_value in expected.items():
            _assert_ir_equal(actual[key], exp_value, f"{path}.{key}" if path else key)
        return
    if isinstance(expected, list):
        assert isinstance(actual, list), f"{path} expected list"
        assert len(actual) == len(expected), f"{path} length mismatch"
        for idx, exp_value in enumerate(expected):
            _assert_ir_equal(actual[idx], exp_value, f"{path}[{idx}]")
        return
    if isinstance(expected, float):
        assert isinstance(actual, (int, float)), f"{path} expected number"
        assert math.isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-12), f"{path} float mismatch"
        return
    assert actual == expected, f"{path} mismatch"


def test_blocksec_example_matches_expected_ir():
    trace_data = json.loads(Path('tests/fixtures/blocksec_IF_example.json').read_text())
    expected = json.loads(Path('tests/fixtures/ir_b_expected.json').read_text())
    ir = _order_ir_dict(build_blocksec_ir(trace_data, TX_HASH))
    _assert_ir_equal(ir, expected)
