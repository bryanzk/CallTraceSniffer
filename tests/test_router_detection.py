"""
测试Router地址识别函数
"""
import pytest
from calltrace.services.converter import TransactionConverter
from calltrace.utils.address import is_router_address, ROUTER_ADDRESSES


class TestRouterDetection:
    """测试is_router_address函数"""
    
    def test_known_router_addresses(self):
        """测试已知Router地址识别"""
        for router_addr in ROUTER_ADDRESSES:
            assert is_router_address(router_addr) == True
            # 测试小写
            assert is_router_address(router_addr.lower()) == True
            # 测试大写
            assert is_router_address(router_addr.upper()) == True
    
    def test_case_insensitive(self):
        """测试大小写不敏感"""
        router_addr = list(ROUTER_ADDRESSES)[0]
        assert is_router_address(router_addr.lower()) == True
        assert is_router_address(router_addr.upper()) == True
        assert is_router_address(router_addr) == True
    
    def test_empty_address(self):
        """测试空地址"""
        assert is_router_address("") == False
        assert is_router_address(None) == False
    
    def test_unknown_address(self):
        """测试未知地址返回False"""
        unknown_addr = "0x1234567890123456789012345678901234567890"
        assert is_router_address(unknown_addr) == False
    
    def test_address_format_validation(self):
        """测试地址格式验证"""
        # 有效地址格式但不在Router列表中
        valid_addr = "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"
        assert is_router_address(valid_addr) == False
        
        # 无效地址格式
        invalid_addr = "not_an_address"
        assert is_router_address(invalid_addr) == False
    
    def test_router_address_with_checksum(self):
        """测试带校验和的Router地址"""
        router_addr = list(ROUTER_ADDRESSES)[0]
        # 混合大小写（EIP-55校验和格式）
        checksum_addr = router_addr[:2] + router_addr[2:].swapcase()
        assert is_router_address(checksum_addr) == True
    
    def test_partial_match(self):
        """测试部分匹配（不应该匹配）"""
        router_addr = list(ROUTER_ADDRESSES)[0]
        partial = router_addr[:-1]  # 少一个字符
        assert is_router_address(partial) == False
        
        extended = router_addr + "0"  # 多一个字符
        assert is_router_address(extended) == False

