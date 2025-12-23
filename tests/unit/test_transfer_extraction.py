"""
测试Transfer提取函数
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'src'))

import pytest
from calltrace.services.converter import TransactionConverter
from calltrace.utils.address import is_router_address
from calltrace.config import config

converter = TransactionConverter()
ROUTER_ADDRESSES = config.ROUTER_ADDRESSES


class TestTransferExtraction:
    """测试extract_transfers_from_data函数"""
    
    def test_transfer_by_selector(self, sample_data_map):
        """测试通过selector识别transfer（0xa9059cbb）"""
        transfers = converter.extract_transfers_from_data(sample_data_map)
        # 应该找到多个transfer
        assert len(transfers) > 0
        # 验证所有transfer都有正确的字段
        for transfer in transfers:
            assert 'from' in transfer
            assert 'to' in transfer
            assert 'token' in transfer
            assert 'amount' in transfer
            assert 'type' in transfer
            assert 'gasCost' in transfer
            assert 'gasUsed' in transfer
            assert 'node_id' in transfer
    
    def test_transfer_by_method_name(self):
        """测试通过method name识别transfer"""
        data_map = {
            "1": {
                "invocation": {
                    "address": "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
                    "fromAddress": "0x1111111111111111111111111111111111111111",
                    "selector": "0x12345678",  # 不是transfer selector
                    "decodedMethod": {
                        "name": "transfer",  # 但method name是transfer
                        "callParams": [
                            {"name": "to", "value": "0x2222222222222222222222222222222222222222"},
                            {"name": "amount", "value": "1000000"}
                        ]
                    },
                    "gasUsed": 5000
                }
            }
        }
        transfers = converter.extract_transfers_from_data(data_map)
        assert len(transfers) == 1
        assert transfers[0]['amount'] == "1000000"
    
    def test_transfer_exclude_event(self):
        """测试排除transfer event"""
        data_map = {
            "1": {
                "invocation": {
                    "address": "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
                    "fromAddress": "0x1111111111111111111111111111111111111111",
                    "decodedMethod": {
                        "name": "TransferEvent",  # 包含transfer但是event
                        "callParams": []
                    },
                    "gasUsed": 0
                }
            }
        }
        transfers = converter.extract_transfers_from_data(data_map)
        assert len(transfers) == 0
    
    def test_transfer_parameter_variants(self):
        """测试参数名变体（recipient/to/dst/destination, amount/value/wad/quantity）"""
        variants = [
            ({"name": "recipient", "value": "0x2222222222222222222222222222222222222222"}, 
             {"name": "amount", "value": "1000000"}),
            ({"name": "to", "value": "0x2222222222222222222222222222222222222222"}, 
             {"name": "value", "value": "2000000"}),
            ({"name": "dst", "value": "0x2222222222222222222222222222222222222222"}, 
             {"name": "wad", "value": "3000000"}),
            ({"name": "destination", "value": "0x2222222222222222222222222222222222222222"}, 
             {"name": "quantity", "value": "4000000"}),
        ]
        
        for i, (recipient_param, amount_param) in enumerate(variants, 1):
            data_map = {
                str(i): {
                    "invocation": {
                        "address": "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
                        "fromAddress": "0x1111111111111111111111111111111111111111",
                        "selector": "0xa9059cbb",
                        "decodedMethod": {
                            "name": "transfer",
                            "callParams": [recipient_param, amount_param]
                        },
                        "gasUsed": 5000
                    }
                }
            }
            transfers = converter.extract_transfers_from_data(data_map)
            assert len(transfers) == 1
            assert transfers[0]['to'] == recipient_param['value']
            assert transfers[0]['amount'] == str(amount_param['value']).replace(',', '')
    
    def test_transfer_from_call_data(self):
        """测试从callData解析（当decodedMethod缺失时）"""
        # callData: 0xa9059cbb + recipient (32 bytes) + amount (32 bytes)
        recipient = "0x2222222222222222222222222222222222222222"
        amount = 1000000
        # 转换为hex
        recipient_hex = recipient[2:].zfill(64)  # 64 hex chars
        amount_hex = hex(amount)[2:].zfill(64)  # 64 hex chars
        call_data = f"0xa9059cbb{recipient_hex}{amount_hex}"
        
        data_map = {
            "1": {
                "invocation": {
                    "address": "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
                    "fromAddress": "0x1111111111111111111111111111111111111111",
                    "selector": "0xa9059cbb",
                    "callData": call_data,
                    "gasUsed": 5000
                }
            }
        }
        transfers = converter.extract_transfers_from_data(data_map)
        assert len(transfers) == 1
        assert transfers[0]['to'].lower() == recipient.lower()
        assert transfers[0]['amount'] == str(amount)
    
    def test_transfer_type_router(self):
        """测试Router类型transfer（from或to是Router地址）"""
        router_addr = list(ROUTER_ADDRESSES)[0]
        
        # from是Router
        data_map = {
            "1": {
                "invocation": {
                    "address": "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
                    "fromAddress": router_addr,
                    "selector": "0xa9059cbb",
                    "decodedMethod": {
                        "name": "transfer",
                        "callParams": [
                            {"name": "to", "value": "0x2222222222222222222222222222222222222222"},
                            {"name": "amount", "value": "1000000"}
                        ]
                    },
                    "gasUsed": 23000
                }
            }
        }
        transfers = converter.extract_transfers_from_data(data_map)
        assert len(transfers) == 1
        assert transfers[0]['type'] == 'Router'
        
        # to是Router
        data_map2 = {
            "1": {
                "invocation": {
                    "address": "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
                    "fromAddress": "0x1111111111111111111111111111111111111111",
                    "selector": "0xa9059cbb",
                    "decodedMethod": {
                        "name": "transfer",
                        "callParams": [
                            {"name": "to", "value": router_addr},
                            {"name": "amount", "value": "1000000"}
                        ]
                    },
                    "gasUsed": 23000
                }
            }
        }
        transfers2 = converter.extract_transfers_from_data(data_map2)
        assert len(transfers2) == 1
        assert transfers2[0]['type'] == 'Router'
    
    def test_transfer_type_direct(self):
        """测试Direct类型transfer（普通转账）"""
        data_map = {
            "1": {
                "invocation": {
                    "address": "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
                    "fromAddress": "0x1111111111111111111111111111111111111111",
                    "selector": "0xa9059cbb",
                    "decodedMethod": {
                        "name": "transfer",
                        "callParams": [
                            {"name": "to", "value": "0x2222222222222222222222222222222222222222"},
                            {"name": "amount", "value": "1000000"}
                        ]
                    },
                    "gasUsed": 5000
                }
            }
        }
        transfers = converter.extract_transfers_from_data(data_map)
        assert len(transfers) == 1
        assert transfers[0]['type'] == 'Direct'
    
    def test_transfer_type_virtual(self):
        """测试Virtual类型transfer（from==to或from为空）"""
        # from == to
        data_map1 = {
            "1": {
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
        transfers1 = converter.extract_transfers_from_data(data_map1)
        assert len(transfers1) == 1
        assert transfers1[0]['type'] == 'Virtual'
        
        # from为空
        data_map2 = {
            "1": {
                "invocation": {
                    "address": "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
                    "fromAddress": "",
                    "selector": "0xa9059cbb",
                    "decodedMethod": {
                        "name": "transfer",
                        "callParams": [
                            {"name": "to", "value": "0x2222222222222222222222222222222222222222"},
                            {"name": "amount", "value": "1000000"}
                        ]
                    },
                    "gasUsed": 0
                }
            }
        }
        transfers2 = converter.extract_transfers_from_data(data_map2)
        assert len(transfers2) == 1
        assert transfers2[0]['type'] == 'Virtual'
    
    def test_gas_used_extraction(self):
        """测试Gas信息提取"""
        data_map = {
            "1": {
                "invocation": {
                    "address": "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
                    "fromAddress": "0x1111111111111111111111111111111111111111",
                    "selector": "0xa9059cbb",
                    "decodedMethod": {
                        "name": "transfer",
                        "callParams": [
                            {"name": "to", "value": "0x2222222222222222222222222222222222222222"},
                            {"name": "amount", "value": "1000000"}
                        ]
                    },
                    "gasUsed": 8862
                }
            }
        }
        transfers = converter.extract_transfers_from_data(data_map)
        assert len(transfers) == 1
        assert transfers[0]['gasUsed'] == 8862
        assert transfers[0]['gasCost'] == 8862  # gasCost应该等于gasUsed
    
    def test_gas_used_none_or_zero(self):
        """测试gasUsed为None/0的处理"""
        # gasUsed为None
        data_map1 = {
            "1": {
                "invocation": {
                    "address": "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
                    "fromAddress": "0x1111111111111111111111111111111111111111",
                    "selector": "0xa9059cbb",
                    "decodedMethod": {
                        "name": "transfer",
                        "callParams": [
                            {"name": "to", "value": "0x2222222222222222222222222222222222222222"},
                            {"name": "amount", "value": "1000000"}
                        ]
                    },
                    "gasUsed": None
                }
            }
        }
        transfers1 = converter.extract_transfers_from_data(data_map1)
        assert len(transfers1) == 1
        assert transfers1[0]['gasUsed'] == 0
        assert transfers1[0]['gasCost'] == 0
        
        # gasUsed为0
        data_map2 = {
            "1": {
                "invocation": {
                    "address": "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
                    "fromAddress": "0x1111111111111111111111111111111111111111",
                    "selector": "0xa9059cbb",
                    "decodedMethod": {
                        "name": "transfer",
                        "callParams": [
                            {"name": "to", "value": "0x2222222222222222222222222222222222222222"},
                            {"name": "amount", "value": "1000000"}
                        ]
                    },
                    "gasUsed": 0
                }
            }
        }
        transfers2 = converter.extract_transfers_from_data(data_map2)
        assert len(transfers2) == 1
        assert transfers2[0]['gasUsed'] == 0
        assert transfers2[0]['gasCost'] == 0
    
    def test_empty_data_map(self, empty_data_map):
        """测试空dataMap"""
        transfers = converter.extract_transfers_from_data(empty_data_map)
        assert transfers == []
    
    def test_invalid_node_data_structure(self):
        """测试无效node_data结构"""
        data_map = {
            "1": "not_a_dict",
            "2": None,
            "3": {
                "not_invocation": {}
            }
        }
        transfers = converter.extract_transfers_from_data(data_map)
        assert transfers == []
    
    def test_missing_invocation_field(self):
        """测试缺少invocation字段"""
        data_map = {
            "1": {
                "not_invocation": {}
            }
        }
        transfers = converter.extract_transfers_from_data(data_map)
        assert transfers == []
    
    def test_missing_recipient_or_amount(self):
        """测试缺少recipient或amount的情况"""
        # 只有recipient，没有amount
        data_map1 = {
            "1": {
                "invocation": {
                    "address": "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
                    "fromAddress": "0x1111111111111111111111111111111111111111",
                    "selector": "0xa9059cbb",
                    "decodedMethod": {
                        "name": "transfer",
                        "callParams": [
                            {"name": "to", "value": "0x2222222222222222222222222222222222222222"}
                            # 缺少amount
                        ]
                    },
                    "gasUsed": 5000
                }
            }
        }
        transfers1 = converter.extract_transfers_from_data(data_map1)
        assert len(transfers1) == 0
        
        # 只有amount，没有recipient
        data_map2 = {
            "1": {
                "invocation": {
                    "address": "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
                    "fromAddress": "0x1111111111111111111111111111111111111111",
                    "selector": "0xa9059cbb",
                    "decodedMethod": {
                        "name": "transfer",
                        "callParams": [
                            {"name": "amount", "value": "1000000"}
                            # 缺少to
                        ]
                    },
                    "gasUsed": 5000
                }
            }
        }
        transfers2 = converter.extract_transfers_from_data(data_map2)
        assert len(transfers2) == 0
    
    def test_amount_with_commas(self):
        """测试amount值中的逗号处理"""
        data_map = {
            "1": {
                "invocation": {
                    "address": "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
                    "fromAddress": "0x1111111111111111111111111111111111111111",
                    "selector": "0xa9059cbb",
                    "decodedMethod": {
                        "name": "transfer",
                        "callParams": [
                            {"name": "to", "value": "0x2222222222222222222222222222222222222222"},
                            {"name": "amount", "value": "1,000,000"}  # 带逗号
                        ]
                    },
                    "gasUsed": 5000
                }
            }
        }
        transfers = converter.extract_transfers_from_data(data_map)
        assert len(transfers) == 1
        assert transfers[0]['amount'] == "1000000"  # 逗号应该被移除
