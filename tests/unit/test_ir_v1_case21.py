"""
BlockSec IR V1 skeleton alignment for case21.
"""
import sys
import os
import json
from pathlib import Path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'src'))

from calltrace.services.ir_v1_blocksec import build_blocksec_ir


def test_case21_ir_structure():
    data = json.loads(Path('local/output/case21_blocksec_data.json').read_text())
    trace_data = data.get('trace_data', {})
    ir = build_blocksec_ir(trace_data, data.get('tx_hash'))

    assert ir.get('tx_hash') == data.get('tx_hash')
    root = ir.get('rootTrace', {})
    assert root.get('type') == 'swap'
    assert 'swap' in root
    assert 'transfer' in root


def test_case21_matches_ir_test_case():
    data = json.loads(Path('local/output/case21_blocksec_data.json').read_text())
    trace_data = data.get('trace_data', {})
    ir = build_blocksec_ir(trace_data, data.get('tx_hash'))

    expected_cases = json.loads(Path('local/new-ir-from-yixin/IR_test_cases.json').read_text())
    expected = next(c for c in expected_cases if c.get('tx_hash') == data.get('tx_hash'))
    assert ir == expected


def test_case1_matches_ir_test_case():
    tx_hash = '0xe42c7f10664571e96b425333a7a06fae1de65dd30eb871d84ceb559cceed00a6'
    trace_data = json.loads(Path(
        'local/output/0xe42c7f10664571e96b425333a7a06fae1de65dd30eb871d84ceb559cceed00a6_blocksec_trace.json'
    ).read_text())
    ir = build_blocksec_ir(trace_data, tx_hash)

    expected_cases = json.loads(Path('local/new-ir-from-yixin/IR_test_cases.json').read_text())
    expected = next(c for c in expected_cases if c.get('tx_hash') == tx_hash)
    assert ir == expected
