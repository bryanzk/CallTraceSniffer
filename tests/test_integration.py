"""
集成测试 - 测试完整的数据处理流程
"""
import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import process_tx_data
from calltrace.services.converter import TransactionConverter
from calltrace.utils.address import
from calltrace.services.converter import TransactionConverter

converter = TransactionConverter() (
    extract_transfers_from_data,
    extract_swaps_from_data,
    build_execution_tree_simplified
)


class TestIntegration:
    """测试process_tx_data完整流程"""
    
    def test_complete_flow_with_real_data(self, sample_trace_data):
        """测试使用真实trace_data结构的完整流程"""
        result = process_tx_data(sample_trace_data)
        
        assert result is not None
        assert 'swaps' in result
        assert 'transfers' in result
        assert 'execution_tree' in result
        assert 'stats' in result
        assert 'formatted_output' in result
    
    def test_data_completeness(self, sample_trace_data):
        """测试数据完整性"""
        result = process_tx_data(sample_trace_data)
        
        # 检查所有字段都存在
        assert 'swaps' in result
        assert 'transfers' in result
        assert 'execution_tree' in result
        assert 'stats' in result
        assert 'formatted_output' in result
        
        # 检查数据类型
        assert isinstance(result['swaps'], list)
        assert isinstance(result['transfers'], list)
        assert isinstance(result['execution_tree'], dict)
        assert isinstance(result['stats'], dict)
        assert isinstance(result['formatted_output'], str)
    
    def test_statistics_accuracy(self, sample_trace_data):
        """测试统计值准确性"""
        result = process_tx_data(sample_trace_data)
        stats = result['stats']
        
        # 验证统计值
        assert stats['swaps_count'] == len(result['swaps'])
        assert stats['transfers_count'] == len(result['transfers'])
        assert stats['router_count'] == sum(1 for t in result['transfers'] if t.get('type') == 'Router')
        assert stats['direct_count'] == sum(1 for t in result['transfers'] if t.get('type') == 'Direct')
        assert stats['virtual_count'] == sum(1 for t in result['transfers'] if t.get('type') == 'Virtual')
        assert stats['total_gas'] == sum(t.get('gasCost', 0) for t in result['transfers'])
    
    def test_trace_data_none(self):
        """测试trace_data为None"""
        result = process_tx_data(None)
        assert result is None
    
    def test_missing_datamap(self):
        """测试缺少dataMap"""
        trace_data = {
            "tx_hash": "0x123",
            "mainTrace": []
            # 缺少dataMap
        }
        result = process_tx_data(trace_data)
        # 应该能处理，但结果可能为空
        assert result is not None
        assert len(result['transfers']) == 0
        assert len(result['swaps']) == 0
    
    def test_missing_maintrace(self):
        """测试缺少mainTrace"""
        trace_data = {
            "tx_hash": "0x123",
            "dataMap": {}
            # 缺少mainTrace
        }
        result = process_tx_data(trace_data)
        # 应该能处理
        assert result is not None
        assert len(result['swaps']) == 0
    
    def test_empty_data_structure(self):
        """测试空数据结构"""
        trace_data = {
            "tx_hash": "0x123",
            "dataMap": {},
            "mainTrace": []
        }
        result = process_tx_data(trace_data)
        assert result is not None
        assert len(result['swaps']) == 0
        assert len(result['transfers']) == 0
        assert len(result['execution_tree']['root_nodes']) == 0
        assert result['stats']['swaps_count'] == 0
        assert result['stats']['transfers_count'] == 0
    
    def test_formatted_output_structure(self, sample_trace_data):
        """测试格式化输出结构"""
        result = process_tx_data(sample_trace_data)
        output = result['formatted_output']
        
        # 验证输出包含关键部分
        assert "TX:" in output
        assert "Swaps:" in output
        assert "ExecutionTree:" in output
        assert "Transfers:" in output
    
    def test_end_to_end_data_flow(self, sample_trace_data):
        """测试端到端数据流"""
        # 手动执行各个步骤
        data_map = sample_trace_data.get('dataMap', {})
        main_trace = sample_trace_data.get('mainTrace', [])
        
        transfers = converter.converter.extract_transfers_from_data(data_map)
        swaps = converter.converter.extract_swaps_from_data(data_map, main_trace)
        execution_tree = converter.converter.build_execution_tree_simplified(swaps, main_trace, data_map)
        
        # 使用process_tx_data
        result = process_tx_data(sample_trace_data)
        
        # 验证结果一致
        assert len(result['transfers']) == len(transfers)
        assert len(result['swaps']) == len(swaps)
        assert len(result['execution_tree']['root_nodes']) == len(execution_tree['root_nodes'])

