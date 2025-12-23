"""
地址处理工具函数
"""
from typing import Optional
from ..config import config


def format_address(addr: Optional[str], length: int = 10) -> str:
    """格式化地址显示"""
    if not addr or addr == 'N/A' or addr == '':
        return 'N/A'
    addr_lower = addr.lower()
    if len(addr) > length + 3:
        return addr[:length] + '...'
    return addr


def is_router_address(addr: Optional[str]) -> bool:
    """判断是否为Router地址"""
    if not addr:
        return False
    return addr.lower() in [r.lower() for r in config.ROUTER_ADDRESSES]

