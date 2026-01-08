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


def _assert_ir_equal(actual, expected, path=""):
    if isinstance(expected, dict):
        assert isinstance(actual, dict), f"{path} expected dict"
        assert set(actual.keys()) == set(expected.keys()), f"{path} keys mismatch"
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
    ir = build_blocksec_ir(trace_data, TX_HASH)
    _assert_ir_equal(ir, expected)
