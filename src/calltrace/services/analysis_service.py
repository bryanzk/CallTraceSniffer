from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from ..config import config
from ..services.extractor import BlockSecExtractor
from ..services.ir_v1_blocksec import _parse_int, build_blocksec_ir
from ..services.mermaid_dag import build_mermaid_dag
from ..utils.ir_format import serialize_ir_payload


@dataclass(frozen=True)
class RouterConfig:
    """路由器配置，用于依赖注入"""
    router_addresses: List[str]

    @classmethod
    def from_global_config(cls) -> RouterConfig:
        """从全局配置创建 RouterConfig（向后兼容）"""
        return cls(router_addresses=list(config.ROUTER_ADDRESSES))


def count_ir_nodes(node: Optional[dict]) -> Tuple[int, int]:
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
    router_config: Optional[RouterConfig] = None,
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


def _use_fixture() -> bool:
    flag = os.getenv("USE_FIXTURE", "")
    return flag.strip().lower() in {"1", "true", "yes", "on"}


def _load_fixture() -> dict:
    root = Path(__file__).resolve().parents[3]
    default_path = root / "tests/fixtures/0xe42c7f10664571e96b425333a7a06fae1de65dd30eb871d84ceb559cceed00a6_blocksec_trace.json"
    fixture_path = Path(os.getenv("FIXTURE_PATH", str(default_path)))
    with fixture_path.open() as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError("Fixture payload must be a JSON object")
    return payload


@dataclass(frozen=True)
class ServiceResult:
    payload: Optional[dict]
    error: Optional[str]
    status_code: int

    @property
    def ok(self) -> bool:
        return self.error is None


class AnalysisService:
    def __init__(
        self,
        cache: dict,
        extractor_factory: Callable[[], BlockSecExtractor] = BlockSecExtractor,
        mermaid_builder: Callable[[dict], str] = build_mermaid_dag,
        router_config: Optional[RouterConfig] = None,
    ) -> None:
        """
        初始化分析服务
        
        Args:
            cache: 缓存字典
            extractor_factory: Extractor 工厂函数
            mermaid_builder: Mermaid DAG 构建函数
            router_config: 路由器配置（可选，默认使用全局config，向后兼容）
        """
        self._cache = cache
        self._extractor_factory = extractor_factory
        self._mermaid_builder = mermaid_builder
        # 向后兼容：如果没有提供 router_config，使用全局配置
        self._router_config = router_config if router_config is not None else RouterConfig.from_global_config()

    def analyze_tx(self, tx_hash: str) -> ServiceResult:
        if _use_fixture():
            trace_data = _load_fixture()
            result = {"success": True, "trace_data": trace_data}
            return self._build_analysis_from_result(
                tx_hash=tx_hash,
                result=result,
                error_default="无法提取交易数据",
                missing_trace_error="未找到trace数据",
            )

        extractor = self._extractor_factory()
        result = asyncio.run(extractor.extract_blocksec_data(tx_hash))
        return self._build_analysis_from_result(
            tx_hash=tx_hash,
            result=result,
            error_default="无法提取交易数据",
            missing_trace_error="未找到trace数据",
        )

    def analyze_simulation(self, sim_url: str) -> ServiceResult:
        try:
            tx_hash, _ = BlockSecExtractor.parse_simulation_url(sim_url)
        except Exception as exc:
            return ServiceResult(payload=None, error=str(exc), status_code=400)

        if _use_fixture():
            trace_data = _load_fixture()
            result = {"success": True, "trace_data": trace_data}
            return self._build_analysis_from_result(
                tx_hash=tx_hash,
                result=result,
                error_default="无法提取模拟交易数据",
                missing_trace_error="未找到simulation trace数据",
            )

        extractor = self._extractor_factory()
        result = asyncio.run(extractor.extract_blocksec_simulation_data(sim_url))
        return self._build_analysis_from_result(
            tx_hash=tx_hash,
            result=result,
            error_default="无法提取模拟交易数据",
            missing_trace_error="未找到simulation trace数据",
        )

    def _build_analysis_from_result(
        self,
        tx_hash: str,
        result: Optional[dict],
        error_default: str,
        missing_trace_error: str,
    ) -> ServiceResult:
        if not result or not result.get("success"):
            error_msg = result.get("error", error_default) if result else error_default
            return ServiceResult(payload=None, error=error_msg, status_code=500)

        trace_data = result.get("trace_data")
        if not trace_data:
            return ServiceResult(payload=None, error=missing_trace_error, status_code=500)

        analysis = process_tx_data(trace_data, tx_hash, result, self._router_config)
        if not analysis:
            return ServiceResult(payload=None, error="数据处理失败", status_code=500)

        mermaid_dag = None
        try:
            mermaid_dag = self._mermaid_builder(analysis["ir_v1"])
        except Exception:
            mermaid_dag = None

        self._cache[tx_hash] = {
            "trace_data": trace_data,
            "analysis": analysis,
        }

        return ServiceResult(
            payload={
                "tx_hash": tx_hash,
                "analysis": analysis,
                "mermaid_dag": mermaid_dag,
            },
            error=None,
            status_code=200,
        )
