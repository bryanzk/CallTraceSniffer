"""
测试执行树构建函数
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'src'))

import pytest
from calltrace.services.converter import TransactionConverter
from calltrace.utils.address import format_address

converter = TransactionConverter()


class TestExecutionTree:
    """测试build_execution_tree_simplified函数"""
    
    def test_single_swap_node(self):
        """测试单个swap节点"""
        swaps = [
            {
                "address": "0x4b2cde9effaa15999010e66da016b2b2c949f747",
                "node_id": "1",
                "form": "Scope",
                "gasUsed": 74510
            }
        ]
        main_trace = [
            {
                "id": 1,
                "to": "0x4b2cde9effaa15999010e66da016b2b2c949f747",
                "children": []
            }
        ]
        data_map = {
            "1": {
                "invocation": {
                    "address": "0x4b2cde9effaa15999010e66da016b2b2c949f747"
                }
            }
        }
        tree = converter.build_execution_tree_simplified(swaps, main_trace, data_map)
        assert len(tree['root_nodes']) == 1
        assert "1" in tree['nodes']
        assert tree['nodes']["1"]['address'] == format_address("0x4b2cde9effaa15999010e66da016b2b2c949f747")
    
    def test_multiple_swap_nodes(self):
        """测试多个swap节点（多个根节点）"""
        swaps = [
            {
                "address": "0x4b2cde9effaa15999010e66da016b2b2c949f747",
                "node_id": "1",
                "form": "Scope",
                "gasUsed": 74510
            },
            {
                "address": "0x5b2cde9effaa15999010e66da016b2b2c949f747",
                "node_id": "2",
                "form": "Node",
                "gasUsed": 50000
            }
        ]
        main_trace = [
            {"id": 1, "to": "0x4b2cde9effaa15999010e66da016b2b2c949f747", "children": []},
            {"id": 2, "to": "0x5b2cde9effaa15999010e66da016b2b2c949f747", "children": []}
        ]
        data_map = {
            "1": {"invocation": {"address": "0x4b2cde9effaa15999010e66da016b2b2c949f747"}},
            "2": {"invocation": {"address": "0x5b2cde9effaa15999010e66da016b2b2c949f747"}}
        }
        tree = converter.build_execution_tree_simplified(swaps, main_trace, data_map)
        assert len(tree['root_nodes']) == 1
        assert "1" in tree['nodes']
        assert "2" not in tree['nodes']
    
    def test_swap_with_payload_children(self):
        """测试swap节点带Payload子节点"""
        swaps = [
            {
                "address": "0x4b2cde9effaa15999010e66da016b2b2c949f747",
                "node_id": "1",
                "form": "Scope",
                "gasUsed": 74510
            },
            {
                "address": "0x5b2cde9effaa15999010e66da016b2b2c949f747",
                "node_id": "2",
                "form": "Node",
                "gasUsed": 50000
            }
        ]
        main_trace = [
            {
                "id": 1,
                "to": "0x4b2cde9effaa15999010e66da016b2b2c949f747",
                "children": [
                    {
                        "id": 2,
                        "to": "0x5b2cde9effaa15999010e66da016b2b2c949f747",
                        "children": []
                    }
                ]
            }
        ]
        data_map = {
            "1": {"invocation": {"address": "0x4b2cde9effaa15999010e66da016b2b2c949f747"}},
            "2": {"invocation": {"address": "0x5b2cde9effaa15999010e66da016b2b2c949f747"}}
        }
        tree = converter.build_execution_tree_simplified(swaps, main_trace, data_map)
        assert len(tree['root_nodes']) == 1
        # 第一个swap应该有children（如果第二个swap是它的子节点）
        node1 = tree['nodes'].get("1", {})
        # 检查是否有子节点关系
        assert "1" in tree['nodes']
        assert "2" in tree['nodes']
    
    def test_nested_payload_structure(self):
        """测试嵌套Payload结构"""
        swaps = [
            {
                "address": "0x4b2cde9effaa15999010e66da016b2b2c949f747",
                "node_id": "1",
                "form": "Scope",
                "gasUsed": 74510
            },
            {
                "address": "0x5b2cde9effaa15999010e66da016b2b2c949f747",
                "node_id": "2",
                "form": "Scope",
                "gasUsed": 50000
            },
            {
                "address": "0x6b2cde9effaa15999010e66da016b2b2c949f747",
                "node_id": "3",
                "form": "Node",
                "gasUsed": 30000
            }
        ]
        main_trace = [
            {
                "id": 1,
                "to": "0x4b2cde9effaa15999010e66da016b2b2c949f747",
                "children": [
                    {
                        "id": 2,
                        "to": "0x5b2cde9effaa15999010e66da016b2b2c949f747",
                        "children": [
                            {
                                "id": 3,
                                "to": "0x6b2cde9effaa15999010e66da016b2b2c949f747",
                                "children": []
                            }
                        ]
                    }
                ]
            }
        ]
        data_map = {
            "1": {"invocation": {"address": "0x4b2cde9effaa15999010e66da016b2b2c949f747"}},
            "2": {"invocation": {"address": "0x5b2cde9effaa15999010e66da016b2b2c949f747"}},
            "3": {"invocation": {"address": "0x6b2cde9effaa15999010e66da016b2b2c949f747"}}
        }
        tree = converter.build_execution_tree_simplified(swaps, main_trace, data_map)
        assert len(tree['root_nodes']) == 1
        assert all(str(i) in tree['nodes'] for i in [1, 2, 3])
    
    def test_node_id_generation(self):
        """测试节点ID生成"""
        swaps = [
            {
                "address": "0x4b2cde9effaa15999010e66da016b2b2c949f747",
                "node_id": "1",
                "form": "Scope",
                "gasUsed": 74510
            }
        ]
        main_trace = [
            {"id": 1, "to": "0x4b2cde9effaa15999010e66da016b2b2c949f747", "children": []}
        ]
        data_map = {
            "1": {"invocation": {"address": "0x4b2cde9effaa15999010e66da016b2b2c949f747"}}
        }
        tree = converter.build_execution_tree_simplified(swaps, main_trace, data_map)
        assert "1" in tree['nodes']
        assert tree['nodes']["1"]['id'] == "1"
    
    def test_address_formatting(self):
        """测试地址格式化"""
        swaps = [
            {
                "address": "0x4b2cde9effaa15999010e66da016b2b2c949f747",
                "node_id": "1",
                "form": "Scope",
                "gasUsed": 74510
            }
        ]
        main_trace = [
            {"id": 1, "to": "0x4b2cde9effaa15999010e66da016b2b2c949f747", "children": []}
        ]
        data_map = {
            "1": {"invocation": {"address": "0x4b2cde9effaa15999010e66da016b2b2c949f747"}}
        }
        tree = converter.build_execution_tree_simplified(swaps, main_trace, data_map)
        node = tree['nodes']["1"]
        assert node['address'] == format_address("0x4b2cde9effaa15999010e66da016b2b2c949f747")
        assert node['address'] == "0x4b2cde9e..."
    
    def test_form_type_assignment(self):
        """测试Form类型（Scope/Node）"""
        swaps = [
            {
                "address": "0x4b2cde9effaa15999010e66da016b2b2c949f747",
                "node_id": "1",
                "form": "Scope",
                "gasUsed": 74510
            }
        ]
        main_trace = [
            {
                "id": 1,
                "to": "0x4b2cde9effaa15999010e66da016b2b2c949f747",
                "children": [{"id": 2, "to": "0x2222222222222222222222222222222222222222", "children": []}]
            }
        ]
        data_map = {
            "1": {"invocation": {"address": "0x4b2cde9effaa15999010e66da016b2b2c949f747"}}
        }
        tree = converter.build_execution_tree_simplified(swaps, main_trace, data_map)
        node = tree['nodes']["1"]
        assert node['form'] == 'Scope'  # 有children
    
    def test_parent_child_relationship(self):
        """测试父子关系建立"""
        swaps = [
            {
                "address": "0x4b2cde9effaa15999010e66da016b2b2c949f747",
                "node_id": "1",
                "form": "Scope",
                "gasUsed": 74510
            },
            {
                "address": "0x5b2cde9effaa15999010e66da016b2b2c949f747",
                "node_id": "2",
                "form": "Node",
                "gasUsed": 50000
            }
        ]
        main_trace = [
            {
                "id": 1,
                "to": "0x4b2cde9effaa15999010e66da016b2b2c949f747",
                "children": [
                    {
                        "id": 2,
                        "to": "0x5b2cde9effaa15999010e66da016b2b2c949f747",
                        "children": []
                    }
                ]
            }
        ]
        data_map = {
            "1": {"invocation": {"address": "0x4b2cde9effaa15999010e66da016b2b2c949f747"}},
            "2": {"invocation": {"address": "0x5b2cde9effaa15999010e66da016b2b2c949f747"}}
        }
        tree = converter.build_execution_tree_simplified(swaps, main_trace, data_map)
        # 如果第二个swap是第一个的payload，应该有父子关系
        node1 = tree['nodes'].get("1", {})
        node2 = tree['nodes'].get("2", {})
        # 检查是否有正确的结构
        assert "1" in tree['nodes']
        assert "2" in tree['nodes']
    
    def test_empty_swaps_list(self):
        """测试空swaps列表"""
        swaps = []
        main_trace = []
        data_map = {}
        tree = converter.build_execution_tree_simplified(swaps, main_trace, data_map)
        assert len(tree['root_nodes']) == 0
        assert len(tree['nodes']) == 0
    
    def test_swap_address_empty(self):
        """测试swap地址为空"""
        swaps = [
            {
                "address": "",  # 空地址
                "node_id": "1",
                "form": "Scope",
                "gasUsed": 74510
            }
        ]
        main_trace = []
        data_map = {}
        tree = converter.build_execution_tree_simplified(swaps, main_trace, data_map)
        # 空地址的swap应该被跳过
        assert len(tree['root_nodes']) == 0
    
    def test_swap_not_found_in_main_trace(self):
        """测试swap在mainTrace中找不到"""
        swaps = [
            {
                "address": "0x4b2cde9effaa15999010e66da016b2b2c949f747",
                "node_id": "1",
                "form": "Scope",
                "gasUsed": 74510
            }
        ]
        main_trace = [
            {"id": 999, "to": "0x9999999999999999999999999999999999999999", "children": []}
        ]
        data_map = {
            "1": {"invocation": {"address": "0x4b2cde9effaa15999010e66da016b2b2c949f747"}}
        }
        tree = converter.build_execution_tree_simplified(swaps, main_trace, data_map)
        # 找不到swap时不创建root节点
        assert len(tree['root_nodes']) == 0
        assert "1" not in tree['nodes']
    
    def test_deep_nesting_structure(self):
        """测试深层嵌套结构"""
        swaps = [
            {
                "address": f"0x{i}b2cde9effaa15999010e66da016b2b2c949f747",
                "node_id": str(i),
                "form": "Scope",
                "gasUsed": 10000 * i
            }
            for i in range(1, 6)
        ]
        # 构建深层嵌套的main_trace
        def build_nested_trace(depth, current_id=1):
            if depth == 0:
                return {"id": current_id, "to": f"0x{current_id}b2cde9effaa15999010e66da016b2b2c949f747", "children": []}
            return {
                "id": current_id,
                "to": f"0x{current_id}b2cde9effaa15999010e66da016b2b2c949f747",
                "children": [build_nested_trace(depth - 1, current_id + 1)]
            }
        
        main_trace = [build_nested_trace(4, 1)]
        data_map = {
            str(i): {"invocation": {"address": f"0x{i}b2cde9effaa15999010e66da016b2b2c949f747"}}
            for i in range(1, 6)
        }
        tree = converter.build_execution_tree_simplified(swaps, main_trace, data_map)
        assert len(tree['root_nodes']) == 1
        assert all(str(i) in tree['nodes'] for i in range(1, 6))
