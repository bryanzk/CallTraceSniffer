"""
集成测试 - 测试完整的数据处理流程
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'src'))

import pytest
from calltrace.api.routes import process_tx_data


class TestIntegration:
    """测试process_tx_data完整流程"""
    
    def test_complete_flow_with_real_data(self, sample_trace_data):
        """测试使用真实trace_data结构的完整流程"""
        result = process_tx_data(sample_trace_data)
        
        assert result is not None
        assert 'ir_v1' in result
        assert 'ir_v1_json' in result
        assert 'stats' in result
    
    def test_data_completeness(self, sample_trace_data):
        """测试数据完整性"""
        result = process_tx_data(sample_trace_data)
        
        # 检查所有字段都存在
        assert 'ir_v1' in result
        assert 'ir_v1_json' in result
        assert 'stats' in result
        
        # 检查数据类型
        assert isinstance(result['ir_v1'], dict)
        assert isinstance(result['ir_v1_json'], str)
        assert isinstance(result['stats'], dict)
    
    def test_statistics_accuracy(self, sample_trace_data):
        """测试统计值准确性"""
        result = process_tx_data(sample_trace_data)
        stats = result['stats']
        
        # 验证统计值
        assert stats['swaps_count'] >= 0
        assert stats['transfers_count'] >= 0
        assert stats['router_count'] >= 0
        assert stats['direct_count'] >= 0
        assert stats['virtual_count'] >= 0
        assert stats['total_gas'] >= 0
        assert stats['transfers_count'] == (
            stats['router_count'] + stats['direct_count'] + stats['virtual_count']
        )
    
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
        assert result['stats']['swaps_count'] == 0
        assert result['stats']['transfers_count'] == 0
    
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
        assert result['stats']['swaps_count'] == 0
    
    def test_empty_data_structure(self):
        """测试空数据结构"""
        trace_data = {
            "tx_hash": "0x123",
            "dataMap": {},
            "mainTrace": []
        }
        result = process_tx_data(trace_data)
        assert result is not None
        assert result['stats']['swaps_count'] == 0
        assert result['stats']['transfers_count'] == 0
        assert result['stats']['swaps_count'] == 0
        assert result['stats']['transfers_count'] == 0
    
    def test_ir_json_contains_tx_hash_first(self, sample_trace_data):
        """测试IR JSON输出包含tx_hash字段"""
        result = process_tx_data(sample_trace_data)
        output = result['ir_v1_json']
        assert "\"tx_hash\"" in output

    def test_complete_flow_with_extra_payloads(self):
        """测试额外payload可被处理"""
        pool = "0x1111111111111111111111111111111111111111"
        token_in = "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        token_out = "0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
        trace_data = {
            "tx_hash": "0xabc",
            "dataMap": {
                "1": {
                    "invocation": {
                        "address": pool,
                        "decodedMethod": {"name": "swap", "callParams": []},
                    }
                }
            },
            "mainTrace": [{"id": 1, "children": []}],
        }
        extra = {
            "token_info": [
                {"address": token_in, "decimals": 6},
                {"address": token_out, "decimals": 18},
            ],
            "fundflow": [
                {"to": pool, "token": token_in, "amount": "1000"},
                {"from": pool, "token": token_out, "amount": "0.5"},
            ],
            "basic_info": {"callData": "0xdeadbeef"},
        }

        result = process_tx_data(trace_data, trace_data["tx_hash"], extra)
        assert result is not None
        assert result["ir_v1"]["rootTrace"]["encoded"] == "0xdeadbeef"
