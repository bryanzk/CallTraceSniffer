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
    data = json.loads(Path('tests/fixtures/case21_blocksec_data.json').read_text())
    trace_data = data.get('trace_data', {})
    ir = build_blocksec_ir(trace_data, data.get('tx_hash'))

    assert ir.get('tx_hash') == data.get('tx_hash')
    root = ir.get('rootTrace', {})
    assert root.get('type') == 'swap'
    assert 'swap' in root
    assert 'transfer' in root

