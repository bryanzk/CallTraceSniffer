"""
测试输出格式化函数
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'src'))

import pytest
from calltrace.services.converter import TransactionConverter
from calltrace.utils.address import format_address

converter = TransactionConverter()


class TestOutputFormatting:
    """测试generate_test_case_format函数"""
    
    def test_complete_format(self):
        """测试完整的test_cases.yaml格式"""
        tx_hash = "0x0807fd45ea0116616ab5cb6b81dd1c395179713fd2465c1d610df14c0c404004"
        swaps = [
            {
                "address": "0x4b2cde9effaa15999010e66da016b2b2c949f747",
                "method": "swap",
                "form": "Scope",
                "gasUsed": 74510
            }
        ]
        execution_tree = {
            "nodes": {
                "1": {
                    "address": format_address("0x4b2cde9effaa15999010e66da016b2b2c949f747"),
                    "form": "Scope",
                    "children": []
                }
            },
            "root_nodes": ["1"]
        }
        transfers = [
            {
                "from": "0x4b2cde9effaa15999010e66da016b2b2c949f747",
                "to": "0x00000000009e50a7ddb7a7b0e2ee6604fd120e49",
                "token": "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
                "amount": "261367284155547648",
                "type": "Direct",
                "gasCost": 8862
            }
        ]
        output = converter.generate_test_case_format(tx_hash, swaps, execution_tree, transfers)
        
        # 验证基本结构
        assert "TX:" in output
        assert tx_hash in output
        assert "Swaps:" in output
        assert "ExecutionTree:" in output
        assert "Transfers:" in output
    
    def test_swaps_section_format(self):
        """测试Swaps部分格式"""
        swaps = [
            {
                "address": "0x4b2cde9effaa15999010e66da016b2b2c949f747",
                "method": "swap",
                "form": "Scope"
            },
            {
                "address": "0x5b2cde9effaa15999010e66da016b2b2c949f747",
                "method": "swap",
                "form": "Node"
            }
        ]
        execution_tree = {"nodes": {}, "root_nodes": []}
        transfers = []
        output = converter.generate_test_case_format("0x123", swaps, execution_tree, transfers)
        
        assert "Swaps: 2" in output
        assert "0x4b2cde9e..." in output
        assert "Form: Scope" in output
        assert "Method: swap" in output
    
    def test_execution_tree_section_format(self):
        """测试ExecutionTree部分格式（根节点和子节点）"""
        swaps = []
        execution_tree = {
            "nodes": {
                "1": {
                    "address": format_address("0x4b2cde9effaa15999010e66da016b2b2c949f747"),
                    "form": "Scope",
                    "children": ["2"],
                    "parent": None
                },
                "2": {
                    "address": format_address("0x5b2cde9effaa15999010e66da016b2b2c949f747"),
                    "form": "Node",
                    "children": [],
                    "parent": "1"
                }
            },
            "root_nodes": ["1"]
        }
        transfers = []
        output = converter.generate_test_case_format("0x123", swaps, execution_tree, transfers)
        
        assert "ExecutionTree: 1 root nodes" in output
        assert "Root[0]:" in output
        assert "Child[0]:" in output
        assert "Form:Scope" in output or "Form: Node" in output
    
    def test_transfers_section_format(self):
        """测试Transfers部分格式（Router/Direct/Virtual图标）"""
        swaps = []
        execution_tree = {"nodes": {}, "root_nodes": []}
        transfers = [
            {
                "from": "0x000000000004444c5dc75cb358380d2e3de08a90",  # Router
                "to": "0x2222222222222222222222222222222222222222",
                "token": "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
                "amount": "1000000",
                "type": "Router",
                "gasCost": 23000
            },
            {
                "from": "0x1111111111111111111111111111111111111111",
                "to": "0x2222222222222222222222222222222222222222",
                "token": "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
                "amount": "2000000",
                "type": "Direct",
                "gasCost": 5000
            },
            {
                "from": "0x3333333333333333333333333333333333333333",
                "to": "0x3333333333333333333333333333333333333333",
                "token": "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
                "amount": "0",
                "type": "Virtual",
                "gasCost": 0
            }
        ]
        output = converter.generate_test_case_format("0x123", swaps, execution_tree, transfers)
        
        assert "Transfers: 3 total" in output
        assert "Router: 1" in output
        assert "Direct: 1" in output
        assert "Virtual: 1" in output
        assert "🔴" in output  # Router图标
        assert "🟢" in output  # Direct图标
        assert "🔵" in output  # Virtual图标
        assert "🏦Router" in output
    
    def test_gas_statistics(self):
        """测试Gas统计信息"""
        swaps = []
        execution_tree = {"nodes": {}, "root_nodes": []}
        transfers = [
            {"gasCost": 23000, "type": "Router"},
            {"gasCost": 5000, "type": "Direct"},
            {"gasCost": 0, "type": "Virtual"}
        ]
        output = converter.generate_test_case_format("0x123", swaps, execution_tree, transfers)
        
        assert "Gas Cost: 28000" in output  # 23000 + 5000 + 0
    
    def test_tx_hash_display(self):
        """测试交易哈希显示"""
        tx_hash = "0x0807fd45ea0116616ab5cb6b81dd1c395179713fd2465c1d610df14c0c404004"
        swaps = []
        execution_tree = {"nodes": {}, "root_nodes": []}
        transfers = []
        output = converter.generate_test_case_format(tx_hash, swaps, execution_tree, transfers)
        
        assert f"TX: {tx_hash}" in output
    
    def test_address_formatting_in_output(self):
        """测试输出中的地址格式化"""
        swaps = [
            {
                "address": "0x4b2cde9effaa15999010e66da016b2b2c949f747",
                "method": "swap",
                "form": "Scope"
            }
        ]
        execution_tree = {
            "nodes": {
                "1": {
                    "address": format_address("0x4b2cde9effaa15999010e66da016b2b2c949f747"),
                    "form": "Scope",
                    "children": []
                }
            },
            "root_nodes": ["1"]
        }
        transfers = [
            {
                "from": "0x4b2cde9effaa15999010e66da016b2b2c949f747",
                "to": "0x00000000009e50a7ddb7a7b0e2ee6604fd120e49",
                "token": "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
                "amount": "261367284155547648",
                "type": "Direct",
                "gasCost": 8862
            }
        ]
        output = converter.generate_test_case_format("0x123", swaps, execution_tree, transfers)
        
        # 地址应该被格式化
        assert "0x4b2cde9e..." in output
        assert "0x00000000..." in output
        assert "0xc02aaa39..." in output
    
    def test_count_statistics(self):
        """测试数量统计"""
        swaps = [
            {"address": "0x111", "method": "swap", "form": "Scope"},
            {"address": "0x222", "method": "swap", "form": "Node"}
        ]
        execution_tree = {
            "nodes": {"1": {"address": "0x111", "form": "Scope", "children": []}},
            "root_nodes": ["1"]
        }
        transfers = [
            {"gasCost": 1000, "type": "Router"},
            {"gasCost": 2000, "type": "Direct"},
            {"gasCost": 3000, "type": "Direct"}
        ]
        output = converter.generate_test_case_format("0x123", swaps, execution_tree, transfers)
        
        assert "Swaps: 2" in output
        assert "Transfers: 3 total" in output
        assert "Router: 1" in output
        assert "Direct: 2" in output
        assert "Virtual: 0" in output
    
    def test_gas_calculation(self):
        """测试Gas计算"""
        swaps = []
        execution_tree = {"nodes": {}, "root_nodes": []}
        transfers = [
            {"gasCost": 23000, "type": "Router"},
            {"gasCost": 5000, "type": "Direct"},
            {"gasCost": 8940, "type": "Direct"}
        ]
        output = converter.generate_test_case_format("0x123", swaps, execution_tree, transfers)
        
        total_gas = 23000 + 5000 + 8940
        assert f"Gas Cost: {total_gas}" in output
    
    def test_empty_swaps_list(self):
        """测试空swaps列表"""
        swaps = []
        execution_tree = {"nodes": {}, "root_nodes": []}
        transfers = []
        output = converter.generate_test_case_format("0x123", swaps, execution_tree, transfers)
        
        assert "Swaps: 0" in output
    
    def test_empty_transfers_list(self):
        """测试空transfers列表"""
        swaps = [{"address": "0x111", "method": "swap", "form": "Scope"}]
        execution_tree = {"nodes": {"1": {"address": "0x111", "form": "Scope", "children": []}}, "root_nodes": ["1"]}
        transfers = []
        output = converter.generate_test_case_format("0x123", swaps, execution_tree, transfers)
        
        assert "Transfers: 0 total" in output
        assert "Gas Cost: 0" in output
    
    def test_empty_execution_tree(self):
        """测试空execution_tree"""
        swaps = [{"address": "0x111", "method": "swap", "form": "Scope"}]
        execution_tree = {"nodes": {}, "root_nodes": []}
        transfers = []
        output = converter.generate_test_case_format("0x123", swaps, execution_tree, transfers)
        
        assert "ExecutionTree: 0 root nodes" in output
    
    def test_multiple_root_nodes(self):
        """测试多个根节点"""
        swaps = [
            {"address": "0x111", "method": "swap", "form": "Scope"},
            {"address": "0x222", "method": "swap", "form": "Node"}
        ]
        execution_tree = {
            "nodes": {
                "1": {"address": format_address("0x111"), "form": "Scope", "children": []},
                "2": {"address": format_address("0x222"), "form": "Node", "children": []}
            },
            "root_nodes": ["1", "2"]
        }
        transfers = []
        output = converter.generate_test_case_format("0x123", swaps, execution_tree, transfers)
        
        assert "ExecutionTree: 2 root nodes" in output
        assert "Root[0]:" in output
        assert "Root[1]:" in output
    
    def test_transfer_details_format(self):
        """测试Transfer详细信息格式"""
        swaps = []
        execution_tree = {"nodes": {}, "root_nodes": []}
        transfers = [
            {
                "from": "0x4b2cde9effaa15999010e66da016b2b2c949f747",
                "to": "0x00000000009e50a7ddb7a7b0e2ee6604fd120e49",
                "token": "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
                "amount": "261367284155547648",
                "type": "Direct",
                "gasCost": 8862
            }
        ]
        output = converter.generate_test_case_format("0x123", swaps, execution_tree, transfers)
        
        assert "Token:" in output
        assert "Amount:" in output
        assert "261367284155547648" in output
        assert "Type: Direct" in output
        assert "Cost: 8862 gas" in output
