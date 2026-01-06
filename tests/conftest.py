"""
pytest配置和测试fixtures
"""
import pytest
from typing import Dict, List

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))


@pytest.fixture
def sample_data_map() -> Dict:
    """示例dataMap，包含transfer和swap调用"""
    return {
        "1": {
            "invocation": {
                "address": "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
                "fromAddress": "0x4b2cde9effaa15999010e66da016b2b2c949f747",
                "selector": "0xa9059cbb",
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
                    "children": []
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
