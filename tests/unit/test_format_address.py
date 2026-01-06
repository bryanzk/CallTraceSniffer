"""
测试地址格式化函数
"""
import pytest
from calltrace.utils.address import format_address


class TestFormatAddress:
    """测试format_address函数"""
    
    def test_normal_address_truncation(self):
        """测试正常地址截断（长度>13）"""
        addr = "0x4b2cde9effaa15999010e66da016b2b2c949f747"
        result = format_address(addr)
        assert result == "0x4b2cde9e..."
        assert len(result) == 13
    
    def test_short_address_no_truncation(self):
        """测试短地址不截断（长度<=13）"""
        addr = "0x1234567890"
        result = format_address(addr)
        assert result == addr
    
    def test_empty_address(self):
        """测试空地址"""
        assert format_address("") == "N/A"
        assert format_address(None) == "N/A"
        assert format_address("N/A") == "N/A"
    
    def test_custom_length(self):
        """测试自定义长度参数"""
        addr = "0x4b2cde9effaa15999010e66da016b2b2c949f747"
        result = format_address(addr, length=6)
        assert result == "0x4b2c..."
        assert len(result) == 9  # 6 + 3
    
    def test_case_insensitive(self):
        """测试大小写不敏感"""
        addr_upper = "0x4B2CDE9EFFAA15999010E66DA016B2B2C949F747"
        addr_lower = "0x4b2cde9effaa15999010e66da016b2b2c949f747"
        result_upper = format_address(addr_upper)
        result_lower = format_address(addr_lower)
        assert result_upper.lower() == result_lower.lower()
    
    def test_exact_length_boundary(self):
        """测试边界情况（正好等于length+3）"""
        addr = "0x1234567890123"  # 15 chars = 12 + 3
        result = format_address(addr, length=12)
        assert result == addr  # 不应该截断
    
    def test_exact_length_plus_one(self):
        """测试正好超过length+3的情况"""
        addr = "0x12345678901234"  # 16 chars = 12 + 4
        result = format_address(addr, length=12)
        assert result == "0x1234567890..."  # 应该截断
    
    def test_very_short_address(self):
        """测试非常短的地址"""
        addr = "0x123"
        result = format_address(addr)
        assert result == addr
    
    def test_zero_address(self):
        """测试零地址"""
        addr = "0x0000000000000000000000000000000000000000"
        result = format_address(addr)
        assert result == "0x00000000..."
        assert len(result) == 13
