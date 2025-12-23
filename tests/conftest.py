"""
pytest配置和测试fixtures
"""
import pytest
import json
from typing import Dict, List

# 导入被测试的模块
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from convert_to_test_case_v2 import (
    format_address,
    is_router_address,
    extract_transfers_from_data,
    extract_swaps_from_data,
    build_execution_tree_simplified,
    generate_test_case_format,
    ROUTER_ADDRESSES
)


@pytest.fixture
def sample_data_map() -> Dict:
    """示例dataMap，包含transfer和swap调用"""
    return {
        "1": {
            "invocation": {
                "address": "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",  # WETH
                "fromAddress": "0x4b2cde9effaa15999010e66da016b2b2c949f747",
                "selector": "0xa9059cbb",  # transfer selector
                "decodedMethod": {
                    "name": "transfer",
                    "callParams": [
                        {"name": "to", "value": "0x00000000009e50a7ddb7a7b0e2ee6604fd120e49"},
                        {"name": "amount", "value": "261367284155547648"}
                    ]
                },
                "gasUsed": 8862
            }
        },
        "2": {
            "invocation": {
                "address": "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
                "fromAddress": "0x00000000009e50a7ddb7a7b0e2ee6604fd120e49",
                "selector": "0xa9059cbb",
                "decodedMethod": {
                    "name": "transfer",
                    "callParams": [
                        {"name": "recipient", "value": "0xb36ec83d844c0579ec2493f10b2087e96bb65460"},
                        {"name": "wad", "value": "255999996669722624"}
                    ]
                },
                "gasUsed": 6062
            }
        },
        "3": {
            "invocation": {
                "address": "0xb2617246e0438d383581f00b5a8c5b5b5b5b5b5b5",
                "fromAddress": "0xb36ec83d844c0579ec2493f10b2087e96bb65460",
                "selector": "0xa9059cbb",
                "decodedMethod": {
                    "name": "transfer",
                    "callParams": [
                        {"name": "dst", "value": "0x4b2cde9effaa15999010e66da016b2b2c949f747"},
                        {"name": "value", "value": "9930559619966812815360"}
                    ]
                },
                "gasUsed": 8940
            }
        },
        "4": {
            "invocation": {
                "address": "0x4b2cde9effaa15999010e66da016b2b2c949f747",
                "fromAddress": "0x00000000009e50a7ddb7a7b0e2ee6604fd120e49",
                "decodedMethod": {
                    "name": "swap",
                    "callParams": []
                },
                "gasUsed": 74510
            }
        },
        "5": {
            "invocation": {
                "address": "0x00000000009e50a7ddb7a7b0e2ee6604fd120e49",
                "fromAddress": "0x4b2cde9effaa15999010e66da016b2b2c949f747",
                "decodedMethod": {
                    "name": "uniswapV3SwapCallback",
                    "callParams": []
                },
                "gasUsed": 31566
            }
        },
        # Transfer with callData only (no decodedMethod)
        "6": {
            "invocation": {
                "address": "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
                "fromAddress": "0x1234567890123456789012345678901234567890",
                "selector": "0xa9059cbb",
                "callData": "0xa9059cbb00000000000000000000000098765432109876543210987654321098765432100000000000000000000000000000000000000000000000000000000000000064",  # transfer(0x9876..., 100)
                "gasUsed": 5000
            }
        },
        # Router address transfer
        "7": {
            "invocation": {
                "address": "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
                "fromAddress": "0x000000000004444c5dc75cb358380d2e3de08a90",  # Router address
                "selector": "0xa9059cbb",
                "decodedMethod": {
                    "name": "transfer",
                    "callParams": [
                        {"name": "to", "value": "0xb36ec83d844c0579ec2493f10b2087e96bb65460"},
                        {"name": "amount", "value": "1000000"}
                    ]
                },
                "gasUsed": 23000
            }
        },
        # Virtual transfer (from == to)
        "8": {
            "invocation": {
                "address": "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
                "fromAddress": "0x1111111111111111111111111111111111111111",
                "selector": "0xa9059cbb",
                "decodedMethod": {
                    "name": "transfer",
                    "callParams": [
                        {"name": "to", "value": "0x1111111111111111111111111111111111111111"},  # same as from
                        {"name": "amount", "value": "0"}
                    ]
                },
                "gasUsed": 0
            }
        }
    }


@pytest.fixture
def sample_main_trace() -> List:
    """示例mainTrace结构"""
    return [
        {
            "id": 1,
            "to": "0x4b2cde9effaa15999010e66da016b2b2c949f747",
            "children": [
                {
                    "id": 4,
                    "to": "0x4b2cde9effaa15999010e66da016b2b2c949f747",
                    "children": [
                        {
                            "id": 5,
                            "to": "0x00000000009e50a7ddb7a7b0e2ee6604fd120e49",
                            "children": []
                        }
                    ]
                }
            ]
        }
    ]


@pytest.fixture
def sample_trace_data(sample_data_map, sample_main_trace) -> Dict:
    """完整的trace_data结构"""
    return {
        "tx_hash": "0x0807fd45ea0116616ab5cb6b81dd1c395179713fd2465c1d610df14c0c404004",
        "dataMap": sample_data_map,
        "mainTrace": sample_main_trace
    }


@pytest.fixture
def empty_data_map() -> Dict:
    """空的dataMap"""
    return {}


@pytest.fixture
def empty_main_trace() -> List:
    """空的mainTrace"""
    return []


@pytest.fixture
def router_addresses():
    """Router地址列表"""
    return ROUTER_ADDRESSES


@pytest.fixture
def expected_transfer_result() -> List[Dict]:
    """期望的transfer提取结果"""
    return [
        {
            "from": "0x4b2cde9effaa15999010e66da016b2b2c949f747",
            "to": "0x00000000009e50a7ddb7a7b0e2ee6604fd120e49",
            "token": "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
            "amount": "261367284155547648",
            "type": "Direct",
            "gasCost": 8862,
            "gasUsed": 8862,
            "node_id": "1"
        }
    ]


@pytest.fixture
def expected_swap_result() -> List[Dict]:
    """期望的swap提取结果"""
    return [
        {
            "address": "0x4b2cde9effaa15999010e66da016b2b2c949f747",
            "method": "swap",
            "node_id": "4",
            "gasUsed": 74510,
            "form": "Scope",
            "depth": 1
        }
    ]

