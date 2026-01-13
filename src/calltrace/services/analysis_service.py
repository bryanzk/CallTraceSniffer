from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from ..services.extractor import BlockSecExtractor
from ..services.mermaid_dag import build_mermaid_dag
from ..utils.analysis_utils import (
    compute_flow_counts,
    count_ir_nodes,
    extract_total_gas,
    extract_transfer_edges,
    process_tx_data,
)


@dataclass(frozen=True)
class RouterConfig:
    """路由器配置，用于依赖注入"""
    router_addresses: List[str]

    @classmethod
    def from_global_config(cls) -> RouterConfig:
        """
        从全局配置创建 RouterConfig（向后兼容）
        
        注意：此方法使用延迟导入以避免模块级别的循环依赖
        """
        # 延迟导入，避免模块级别的全局依赖
        from ..config import config
        return cls(router_addresses=list(config.ROUTER_ADDRESSES))


class FixtureLoader:
    """Fixture 加载器，用于依赖注入，分离测试逻辑"""
    
    def should_use_fixture(self) -> bool:
        """检查是否应该使用 fixture（从环境变量读取）"""
        flag = os.getenv("USE_FIXTURE", "")
        return flag.strip().lower() in {"1", "true", "yes", "on"}
    
    def load_fixture(self) -> dict:
        """加载 fixture 数据"""
        root = Path(__file__).resolve().parents[3]
        default_path = root / "tests/fixtures/0xe42c7f10664571e96b425333a7a06fae1de65dd30eb871d84ceb559cceed00a6_blocksec_trace.json"
        fixture_path = Path(os.getenv("FIXTURE_PATH", str(default_path)))
        with fixture_path.open() as handle:
            payload = json.load(handle)
        if not isinstance(payload, dict):
            raise ValueError("Fixture payload must be a JSON object")
        return payload


# 向后兼容：保留模块级别的函数（已废弃，建议使用 FixtureLoader）
def _use_fixture() -> bool:
    """已废弃：使用 FixtureLoader.should_use_fixture() 代替"""
    loader = FixtureLoader()
    return loader.should_use_fixture()


def _load_fixture() -> dict:
    """已废弃：使用 FixtureLoader.load_fixture() 代替"""
    loader = FixtureLoader()
    return loader.load_fixture()


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
        fixture_loader: Optional[FixtureLoader] = None,
    ) -> None:
        """
        初始化分析服务
        
        Args:
            cache: 缓存字典
            extractor_factory: Extractor 工厂函数
            mermaid_builder: Mermaid DAG 构建函数
            router_config: 路由器配置（可选，默认使用全局config，向后兼容）
            fixture_loader: Fixture 加载器（可选，默认创建新实例，向后兼容）
        """
        self._cache = cache
        self._extractor_factory = extractor_factory
        self._mermaid_builder = mermaid_builder
        # 向后兼容：如果没有提供 router_config，使用全局配置
        self._router_config = router_config if router_config is not None else RouterConfig.from_global_config()
        # 向后兼容：如果没有提供 fixture_loader，创建新实例
        self._fixture_loader = fixture_loader if fixture_loader is not None else FixtureLoader()

    def analyze_tx(self, tx_hash: str) -> ServiceResult:
        # 使用注入的 fixture_loader 而非直接调用模块函数
        if self._fixture_loader.should_use_fixture():
            trace_data = self._fixture_loader.load_fixture()
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
        # 使用注入的 extractor 工厂创建实例，然后调用 parse_simulation_url
        # 保持依赖注入的一致性，而非直接调用 BlockSecExtractor 类
        extractor = self._extractor_factory()
        try:
            tx_hash, _ = extractor.parse_simulation_url(sim_url)
        except Exception as exc:
            return ServiceResult(payload=None, error=str(exc), status_code=400)

        # 使用注入的 fixture_loader 而非直接调用模块函数
        if self._fixture_loader.should_use_fixture():
            trace_data = self._fixture_loader.load_fixture()
            result = {"success": True, "trace_data": trace_data}
            return self._build_analysis_from_result(
                tx_hash=tx_hash,
                result=result,
                error_default="无法提取模拟交易数据",
                missing_trace_error="未找到simulation trace数据",
            )

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
