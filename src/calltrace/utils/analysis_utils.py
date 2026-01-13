"""
分析工具函数模块

包含所有纯函数形式的分析工具，通过参数传递依赖，不依赖全局状态。
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

from ..services.ir_v1_blocksec import _parse_int, build_blocksec_ir
from ..utils.ir_format import serialize_ir_payload

if TYPE_CHECKING:
    from ..services.analysis_service import RouterConfig


def count_ir_nodes(node: Optional[dict]) -> Tuple[int, int]:
    """
    统计 IR 节点中的 swap 和 transfer 数量
    
    Args:
        node: IR 节点字典
    
    Returns:
        (swaps_count, transfers_count)
    """
    if not node or not isinstance(node, dict):
        return 0, 0
    swaps = 1 if node.get("type") == "swap" else 0
    transfers = 1 if node.get("type") == "transfer" else 0
    for child in node.get("callback", []) or []:
        child_swaps, child_transfers = count_ir_nodes(child)
        swaps += child_swaps
        transfers += child_transfers
    return swaps, transfers


def extract_total_gas(trace_data: Optional[dict]) -> int:
    """
    从 trace_data 中提取总 gas 使用量
    
    Args:
        trace_data: 交易追踪数据
    
    Returns:
        总 gas 使用量，如果未找到则返回 0
    """
    gas_flame = trace_data.get("gasFlame", []) if trace_data else []
    if not gas_flame:
        return 0

    def walk(node: dict) -> Optional[int]:
        if not isinstance(node, dict):
            return None
        if node.get("name") == "Actual Gas Used":
            return node.get("value")
        for child in node.get("children", []) or []:
            result = walk(child)
            if result is not None:
                return result
        return None

    for root in gas_flame:
        result = walk(root)
        if result is not None:
            return result
    return 0


def extract_transfer_edges(trace_data: Optional[dict]) -> list[dict]:
    """
    从 trace_data 中提取所有 transfer 边
    
    Args:
        trace_data: 交易追踪数据
    
    Returns:
        transfer 边列表，每个边包含 from, to, token, amount
    """
    data_map = trace_data.get("dataMap", {}) if trace_data else {}
    edges = []
    for entry in data_map.values():
        inv = entry.get("invocation")
        if not inv:
            continue
        method = inv.get("decodedMethod") or {}
        name = method.get("name", "") if isinstance(method, dict) else ""
        if name != "transfer":
            continue
        call_params = method.get("callParams", []) if isinstance(method, dict) else []
        to_addr = ""
        amount = 0
        for param in call_params:
            if param.get("name") in ("to", "recipient", "dst"):
                to_addr = param.get("value", "") or ""
            if param.get("name") in ("amount", "value", "wad"):
                amount = _parse_int(param.get("value")) or 0
        if not to_addr:
            continue
        edges.append({
            "from": (inv.get("fromAddress") or "").lower(),
            "to": to_addr.lower(),
            "token": (inv.get("address") or "").lower(),
            "amount": amount,
        })
    return edges


def compute_flow_counts(
    trace_data: Optional[dict],
    router_addresses: List[str],
) -> Tuple[int, int, int, int]:
    """
    计算转账流统计
    
    Args:
        trace_data: 交易追踪数据
        router_addresses: 路由器地址列表（通过参数注入，而非全局config）
    
    Returns:
        (total, router_count, direct_count, virtual_count)
    """
    edges = extract_transfer_edges(trace_data)
    if not edges:
        return 0, 0, 0, 0

    router_addresses_set = {addr.lower() for addr in router_addresses}

    for edge in edges:
        if edge["from"] and edge["from"] == edge["to"]:
            edge["flow"] = "Virtual"
        elif edge["from"] in router_addresses_set or edge["to"] in router_addresses_set:
            edge["flow"] = "Transfer"
        else:
            edge["flow"] = "Direct"

    incoming: Dict[Tuple[str, str, int], list[dict]] = {}
    outgoing = []
    for edge in edges:
        if edge["flow"] != "Transfer":
            continue
        if edge["to"] in router_addresses_set:
            key = (edge["to"], edge["token"], edge["amount"])
            incoming.setdefault(key, []).append(edge)
        elif edge["from"] in router_addresses_set:
            outgoing.append(edge)

    merged = set()
    direct_from_merge = 0
    for edge in outgoing:
        key = (edge["from"], edge["token"], edge["amount"])
        candidates = incoming.get(key, [])
        if len(candidates) == 1:
            merged.add(id(edge))
            merged.add(id(candidates[0]))
            direct_from_merge += 1

    router_count = 0
    direct_count = 0
    virtual_count = 0
    for edge in edges:
        if edge["flow"] == "Virtual":
            virtual_count += 1
            continue
        if id(edge) in merged:
            continue
        if edge["flow"] == "Transfer":
            router_count += 1
        elif edge["flow"] == "Direct":
            direct_count += 1

    direct_count += direct_from_merge
    total = router_count + direct_count + virtual_count
    return total, router_count, direct_count, virtual_count


def process_tx_data(
    trace_data: dict,
    tx_hash: Optional[str] = None,
    extra: Optional[dict] = None,
    router_config: Optional["RouterConfig"] = None,
) -> Optional[dict]:
    """
    处理交易数据，生成分析结果
    
    Args:
        trace_data: 交易追踪数据
        tx_hash: 交易哈希
        extra: 额外数据
        router_config: 路由器配置（可选，默认使用全局config，向后兼容）
    
    Returns:
        分析结果字典，包含 ir_v1, ir_v1_json, stats
    """
    if not trace_data:
        return None

    # 向后兼容：如果没有提供 router_config，使用全局配置
    if router_config is None:
        from ..services.analysis_service import RouterConfig
        router_config = RouterConfig.from_global_config()

    ir_v1 = build_blocksec_ir(trace_data, tx_hash, extra)
    ir_v1_json = serialize_ir_payload(ir_v1, tx_hash)
    swaps_count, _ = count_ir_nodes(ir_v1.get("rootTrace"))
    transfers_count, router_count, direct_count, virtual_count = compute_flow_counts(
        trace_data, router_config.router_addresses
    )
    total_gas = extract_total_gas(trace_data)

    return {
        "ir_v1": ir_v1,
        "ir_v1_json": ir_v1_json,
        "stats": {
            "swaps_count": swaps_count,
            "transfers_count": transfers_count,
            "router_count": router_count,
            "direct_count": direct_count,
            "virtual_count": virtual_count,
            "total_gas": total_gas,
        },
    }
