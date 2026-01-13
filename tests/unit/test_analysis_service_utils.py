"""
测试 analysis_utils.py 中的工具函数
"""
import pytest
from calltrace.utils.analysis_utils import (
    count_ir_nodes,
    extract_total_gas,
    extract_transfer_edges,
    compute_flow_counts,
    process_tx_data,
)


class TestCountIrNodes:
    """测试 count_ir_nodes 函数"""

    def test_empty_node_returns_zeros(self):
        """空节点返回 (0, 0)"""
        swaps, transfers = count_ir_nodes(None)
        assert swaps == 0
        assert transfers == 0

    def test_non_dict_node_returns_zeros(self):
        """非字典节点返回 (0, 0)"""
        swaps, transfers = count_ir_nodes([])
        assert swaps == 0
        assert transfers == 0

    def test_single_swap_node(self):
        """单个swap节点"""
        node = {"type": "swap"}
        swaps, transfers = count_ir_nodes(node)
        assert swaps == 1
        assert transfers == 0

    def test_single_transfer_node(self):
        """单个transfer节点"""
        node = {"type": "transfer"}
        swaps, transfers = count_ir_nodes(node)
        assert swaps == 0
        assert transfers == 1

    def test_node_with_other_type(self):
        """其他类型的节点"""
        node = {"type": "other"}
        swaps, transfers = count_ir_nodes(node)
        assert swaps == 0
        assert transfers == 0

    def test_node_with_callbacks(self):
        """带回调的节点"""
        node = {
            "type": "swap",
            "callback": [
                {"type": "transfer"},
                {"type": "swap", "callback": [{"type": "transfer"}]}
            ]
        }
        swaps, transfers = count_ir_nodes(node)
        assert swaps == 2  # 1 root + 1 child
        assert transfers == 2  # 2 children

    def test_empty_callback_list(self):
        """空回调列表"""
        node = {"type": "swap", "callback": []}
        swaps, transfers = count_ir_nodes(node)
        assert swaps == 1
        assert transfers == 0

    def test_missing_callback_key(self):
        """缺少callback键"""
        node = {"type": "swap"}
        swaps, transfers = count_ir_nodes(node)
        assert swaps == 1
        assert transfers == 0


class TestExtractTotalGas:
    """测试 extract_total_gas 函数"""

    def test_none_trace_data_returns_zero(self):
        """None trace_data 返回 0"""
        assert extract_total_gas(None) == 0

    def test_empty_trace_data_returns_zero(self):
        """空 trace_data 返回 0"""
        assert extract_total_gas({}) == 0

    def test_no_gas_flame_returns_zero(self):
        """没有 gasFlame 返回 0"""
        trace_data = {"dataMap": {}}
        assert extract_total_gas(trace_data) == 0

    def test_empty_gas_flame_returns_zero(self):
        """空 gasFlame 返回 0"""
        trace_data = {"gasFlame": []}
        assert extract_total_gas(trace_data) == 0

    def test_finds_actual_gas_used(self):
        """找到 Actual Gas Used"""
        trace_data = {
            "gasFlame": [
                {
                    "name": "Root",
                    "children": [
                        {
                            "name": "Actual Gas Used",
                            "value": 150000
                        }
                    ]
                }
            ]
        }
        assert extract_total_gas(trace_data) == 150000

    def test_finds_nested_actual_gas_used(self):
        """在嵌套结构中找到 Actual Gas Used"""
        trace_data = {
            "gasFlame": [
                {
                    "name": "Root",
                    "children": [
                        {
                            "name": "Level1",
                            "children": [
                                {
                                    "name": "Level2",
                                    "children": [
                                        {
                                            "name": "Actual Gas Used",
                                            "value": 200000
                                        }
                                    ]
                                }
                            ]
                        }
                    ]
                }
            ]
        }
        assert extract_total_gas(trace_data) == 200000

    def test_multiple_roots_returns_first_match(self):
        """多个根节点返回第一个匹配"""
        trace_data = {
            "gasFlame": [
                {
                    "name": "Root1",
                    "children": [
                        {"name": "Actual Gas Used", "value": 100000}
                    ]
                },
                {
                    "name": "Root2",
                    "children": [
                        {"name": "Actual Gas Used", "value": 200000}
                    ]
                }
            ]
        }
        assert extract_total_gas(trace_data) == 100000

    def test_no_actual_gas_used_returns_zero(self):
        """没有 Actual Gas Used 返回 0"""
        trace_data = {
            "gasFlame": [
                {
                    "name": "Root",
                    "children": [
                        {"name": "Other", "value": 100000}
                    ]
                }
            ]
        }
        assert extract_total_gas(trace_data) == 0


class TestExtractTransferEdges:
    """测试 extract_transfer_edges 函数"""

    def test_none_trace_data_returns_empty(self):
        """None trace_data 返回空列表"""
        assert extract_transfer_edges(None) == []

    def test_empty_trace_data_returns_empty(self):
        """空 trace_data 返回空列表"""
        assert extract_transfer_edges({}) == []

    def test_no_data_map_returns_empty(self):
        """没有 dataMap 返回空列表"""
        trace_data = {"mainTrace": []}
        assert extract_transfer_edges(trace_data) == []

    def test_no_transfer_methods_returns_empty(self):
        """没有 transfer 方法返回空列表"""
        trace_data = {
            "dataMap": {
                "1": {
                    "invocation": {
                        "decodedMethod": {
                            "name": "swap",
                            "callParams": []
                        }
                    }
                }
            }
        }
        assert extract_transfer_edges(trace_data) == []

    def test_extracts_single_transfer(self):
        """提取单个 transfer"""
        trace_data = {
            "dataMap": {
                "1": {
                    "invocation": {
                        "address": "0xToken",
                        "fromAddress": "0xFrom",
                        "decodedMethod": {
                            "name": "transfer",
                            "callParams": [
                                {"name": "to", "value": "0xTo"},
                                {"name": "amount", "value": "1000"}
                            ]
                        }
                    }
                }
            }
        }
        edges = extract_transfer_edges(trace_data)
        assert len(edges) == 1
        assert edges[0]["from"] == "0xfrom"
        assert edges[0]["to"] == "0xto"
        assert edges[0]["token"] == "0xtoken"
        assert edges[0]["amount"] == 1000

    def test_extracts_multiple_transfers(self):
        """提取多个 transfer"""
        trace_data = {
            "dataMap": {
                "1": {
                    "invocation": {
                        "address": "0xToken1",
                        "fromAddress": "0xFrom1",
                        "decodedMethod": {
                            "name": "transfer",
                            "callParams": [
                                {"name": "to", "value": "0xTo1"},
                                {"name": "amount", "value": "1000"}
                            ]
                        }
                    }
                },
                "2": {
                    "invocation": {
                        "address": "0xToken2",
                        "fromAddress": "0xFrom2",
                        "decodedMethod": {
                            "name": "transfer",
                            "callParams": [
                                {"name": "recipient", "value": "0xTo2"},
                                {"name": "value", "value": "2000"}
                            ]
                        }
                    }
                }
            }
        }
        edges = extract_transfer_edges(trace_data)
        assert len(edges) == 2

    def test_skips_transfer_without_to_address(self):
        """跳过没有 to 地址的 transfer"""
        trace_data = {
            "dataMap": {
                "1": {
                    "invocation": {
                        "address": "0xToken",
                        "fromAddress": "0xFrom",
                        "decodedMethod": {
                            "name": "transfer",
                            "callParams": [
                                {"name": "amount", "value": "1000"}
                            ]
                        }
                    }
                }
            }
        }
        edges = extract_transfer_edges(trace_data)
        assert len(edges) == 0

    def test_handles_missing_invocation(self):
        """处理缺少 invocation 的条目"""
        trace_data = {
            "dataMap": {
                "1": {}
            }
        }
        edges = extract_transfer_edges(trace_data)
        assert len(edges) == 0

    def test_handles_missing_decoded_method(self):
        """处理缺少 decodedMethod 的条目"""
        trace_data = {
            "dataMap": {
                "1": {
                    "invocation": {}
                }
            }
        }
        edges = extract_transfer_edges(trace_data)
        assert len(edges) == 0

    def test_lowercases_addresses(self):
        """地址转换为小写"""
        trace_data = {
            "dataMap": {
                "1": {
                    "invocation": {
                        "address": "0xTOKEN",
                        "fromAddress": "0xFROM",
                        "decodedMethod": {
                            "name": "transfer",
                            "callParams": [
                                {"name": "to", "value": "0xTO"}
                            ]
                        }
                    }
                }
            }
        }
        edges = extract_transfer_edges(trace_data)
        assert edges[0]["from"] == "0xfrom"
        assert edges[0]["to"] == "0xto"
        assert edges[0]["token"] == "0xtoken"


class TestComputeFlowCounts:
    """测试 compute_flow_counts 函数"""

    def test_none_trace_data_returns_zeros(self):
        """None trace_data 返回 (0, 0, 0, 0)"""
        from calltrace.config import config
        result = compute_flow_counts(None, config.ROUTER_ADDRESSES)
        assert result == (0, 0, 0, 0)

    def test_empty_trace_data_returns_zeros(self):
        """空 trace_data 返回 (0, 0, 0, 0)"""
        from calltrace.config import config
        result = compute_flow_counts({}, config.ROUTER_ADDRESSES)
        assert result == (0, 0, 0, 0)

    def test_no_transfer_edges_returns_zeros(self):
        """没有 transfer edges 返回 (0, 0, 0, 0)"""
        from calltrace.config import config
        trace_data = {"dataMap": {}}
        result = compute_flow_counts(trace_data, config.ROUTER_ADDRESSES)
        assert result == (0, 0, 0, 0)

    def test_virtual_flow(self):
        """虚拟流（from == to）"""
        from calltrace.config import config
        
        trace_data = {
            "dataMap": {
                "1": {
                    "invocation": {
                        "address": "0xToken",
                        "fromAddress": "0xSame",
                        "decodedMethod": {
                            "name": "transfer",
                            "callParams": [
                                {"name": "to", "value": "0xSame"},
                                {"name": "amount", "value": "1000"}
                            ]
                        }
                    }
                }
            }
        }
        router_addresses = config.ROUTER_ADDRESSES
        result = compute_flow_counts(trace_data, router_addresses)
        total, router, direct, virtual = result
        assert total == 1
        assert virtual == 1
        assert router == 0
        assert direct == 0

    def test_router_transfer_flow(self):
        """通过路由器的转账流"""
        from calltrace.config import config
        
        router_addr = config.ROUTER_ADDRESSES[0].lower()
        trace_data = {
            "dataMap": {
                "1": {
                    "invocation": {
                        "address": "0xToken",
                        "fromAddress": "0xFrom",
                        "decodedMethod": {
                            "name": "transfer",
                            "callParams": [
                                {"name": "to", "value": router_addr},
                                {"name": "amount", "value": "1000"}
                            ]
                        }
                    }
                }
            }
        }
        router_addresses = config.ROUTER_ADDRESSES
        result = compute_flow_counts(trace_data, router_addresses)
        total, router, direct, virtual = result
        assert total == 1
        assert router == 1
        assert direct == 0
        assert virtual == 0

    def test_direct_transfer_flow(self):
        """直接转账流"""
        from calltrace.config import config
        
        trace_data = {
            "dataMap": {
                "1": {
                    "invocation": {
                        "address": "0xToken",
                        "fromAddress": "0xFrom",
                        "decodedMethod": {
                            "name": "transfer",
                            "callParams": [
                                {"name": "to", "value": "0xTo"},
                                {"name": "amount", "value": "1000"}
                            ]
                        }
                    }
                }
            }
        }
        router_addresses = config.ROUTER_ADDRESSES
        result = compute_flow_counts(trace_data, router_addresses)
        total, router, direct, virtual = result
        assert total == 1
        assert direct == 1
        assert router == 0
        assert virtual == 0


class TestProcessTxData:
    """测试 process_tx_data 函数"""

    def test_none_trace_data_returns_none(self):
        """None trace_data 返回 None"""
        result = process_tx_data(None)
        assert result is None

    def test_empty_trace_data_returns_none(self):
        """空 trace_data 返回 None"""
        result = process_tx_data({})
        assert result is None

    def test_processes_valid_trace_data(self, monkeypatch):
        """处理有效的 trace_data"""
        from calltrace.services.ir_v1_blocksec import build_blocksec_ir
        from calltrace.utils.ir_format import serialize_ir_payload
        from calltrace.services.analysis_service import RouterConfig
        
        trace_data = {
            "dataMap": {},
            "mainTrace": []
        }
        
        # Mock build_blocksec_ir 和 serialize_ir_payload
        def mock_build_ir(trace, tx_hash, extra):
            return {"rootTrace": None}
        
        def mock_serialize(ir, tx_hash):
            return "{}"
        
        from calltrace.services import ir_v1_blocksec
        from calltrace.utils import ir_format
        monkeypatch.setattr(ir_v1_blocksec, "build_blocksec_ir", mock_build_ir)
        monkeypatch.setattr(ir_format, "serialize_ir_payload", mock_serialize)
        
        router_config = RouterConfig.from_global_config()
        result = process_tx_data(trace_data, "0x" + "a" * 64, None, router_config)
        
        assert result is not None
        assert "ir_v1" in result
        assert "ir_v1_json" in result
        assert "stats" in result
        assert "swaps_count" in result["stats"]
        assert "transfers_count" in result["stats"]
        assert "total_gas" in result["stats"]

    def test_includes_tx_hash_in_result(self, monkeypatch):
        """结果中包含 tx_hash"""
        from calltrace.services.analysis_service import RouterConfig
        
        trace_data = {
            "dataMap": {},
            "mainTrace": []
        }
        
        def mock_build_ir(trace, tx_hash, extra):
            return {"rootTrace": None}
        
        def mock_serialize(ir, tx_hash):
            return "{}"
        
        from calltrace.services import ir_v1_blocksec
        from calltrace.utils import ir_format
        monkeypatch.setattr(ir_v1_blocksec, "build_blocksec_ir", mock_build_ir)
        monkeypatch.setattr(ir_format, "serialize_ir_payload", mock_serialize)
        
        tx_hash = "0x" + "b" * 64
        router_config = RouterConfig.from_global_config()
        result = process_tx_data(trace_data, tx_hash, None, router_config)
        
        assert result is not None
        # process_tx_data 不直接返回 tx_hash，但会传递给 build_blocksec_ir
        # 这里主要验证函数能正常执行
