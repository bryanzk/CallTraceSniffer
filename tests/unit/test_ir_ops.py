"""
测试Op_1~Op_5基础逻辑
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'src'))

from calltrace.services.converter import TransactionConverter
from calltrace.config import config


converter = TransactionConverter()


def test_op1_deterministic_direct():
    graph = {
        'nodes': {},
        'edges': [
            {
                'from': '0xaaa',
                'to': config.ROUTER_ADDRESSES[0],
                'token': config.WETH,
                'amount': 100,
                'flow_type': 'Transfer',
                'gasCost': 23000,
                'gasUsed': 23000,
            },
            {
                'from': config.ROUTER_ADDRESSES[0],
                'to': '0xbbb',
                'token': config.WETH,
                'amount': 100,
                'flow_type': 'Transfer',
                'gasCost': 23000,
                'gasUsed': 23000,
            },
        ],
        'exec_order': [],
    }
    converter.apply_op1_deterministic_direct(graph)
    assert len(graph['edges']) == 1
    assert graph['edges'][0]['flow_type'] == 'Direct'
    assert graph['edges'][0]['from'] == '0xaaa'
    assert graph['edges'][0]['to'] == '0xbbb'


def test_op2_virtual_reduction_singleton():
    graph = {
        'nodes': {
            '1': {
                'id': '1',
                'address': '0xpool',
                'singleton_id': '0xpool',
                'node_type': 'CallbackV4',
                'token_in': '0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48',
                'amount_in': 1000,
                'form': 'Scope',
            }
        },
        'edges': [],
        'exec_order': [],
    }
    converter.apply_op2_virtual_reduction(graph)
    virtual_edges = [e for e in graph['edges'] if e.get('flow_type') == 'Virtual']
    assert len(virtual_edges) == 1
    assert virtual_edges[0]['gasCost'] == 0
    assert virtual_edges[0]['from'] == '0xpool'
    assert virtual_edges[0]['to'] == '0xpool'


def test_op3_form_assignment():
    graph = {
        'nodes': {
            '1': {'id': '1', 'node_type': 'Callback', 'form': None, 'payload': []},
            '2': {'id': '2', 'node_type': 'Standard', 'form': None, 'payload': []},
        },
        'edges': [],
        'exec_order': [],
    }
    converter.apply_op3_mandatory_scope(graph)
    assert graph['nodes']['1']['form'] == 'Scope'
    assert graph['nodes']['2']['form'] == 'Node'

def test_op3_form_assignment_v4():
    graph = {
        'nodes': {
            '1': {'id': '1', 'node_type': 'CallbackV4', 'form': None, 'payload': []},
            '2': {'id': '2', 'node_type': 'Standard', 'form': None, 'payload': []},
        },
        'edges': [],
        'exec_order': [],
    }
    converter.apply_op3_mandatory_scope(graph)
    assert graph['nodes']['1']['form'] == 'Scope'
    assert graph['nodes']['2']['form'] == 'Node'


def test_payload_sorting_by_dependency():
    graph = {
        'nodes': {
            'root': {
                'id': 'root',
                'address': '0xroot',
                'form': 'Scope',
                'node_type': 'Callback',
                'token_out': '0xtokenx',
                'payload': [],
            },
            'a': {
                'id': 'a',
                'address': '0xaaa',
                'form': 'Node',
                'node_type': 'Standard',
                'token_in': '0xtokenx',
                'payload': [],
            },
            'b': {
                'id': 'b',
                'address': '0xbbb',
                'form': 'Scope',
                'node_type': 'Callback',
                'token_in': '0xtokeny',
                'payload': [],
            },
        },
        'edges': [
            {'from': '0xaaa', 'to': '0xroot', 'token': '0xtokenx', 'amount': 1, 'flow_type': 'Transfer', 'gasCost': 0, 'gasUsed': 0},
            {'from': '0xbbb', 'to': '0xroot', 'token': '0xtokeny', 'amount': 1, 'flow_type': 'Transfer', 'gasCost': 0, 'gasUsed': 0},
        ],
        'exec_order': ['root', 'b', 'a'],
    }
    converter.apply_payload_from_edges(graph)
    assert graph['nodes']['root']['payload'] == ['a', 'b']


def test_op4_execution_plan():
    graph = {
        'nodes': {
            '1': {
                'id': '1',
                'form': 'Scope',
                'token_in': config.WETH,
                'token_out': '0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48',
                'amount_in': 100,
                'payload': ['2'],
            }
        },
        'edges': [],
        'exec_order': [],
    }
    converter.apply_op4_primitive_conversion(graph)
    plan = graph['nodes']['1']['execution_plan']
    assert plan['preamble']['token'] == '0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48'
    assert plan['postamble']['token'] == config.WETH


def test_op5_engulfing_backward():
    graph = {
        'nodes': {
            '1': {
                'id': '1',
                'form': 'Node',
                'token_in': '0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48',
                'amount_in': 100,
                'token_out': None,
                'amount_out': None,
                'payload': [],
            },
            '2': {
                'id': '2',
                'form': 'Scope',
                'token_out': '0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48',
                'amount_out': 200,
                'payload': [],
            },
        },
        'edges': [],
        'exec_order': ['1', '2'],
    }
    converter.apply_op5_engulfing(graph)
    assert graph['exec_order'][0] == '2'
    assert '1' in graph['nodes']['2']['payload']
