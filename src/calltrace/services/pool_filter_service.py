from __future__ import annotations

"""
当前 pool 查询方式：
- 走 Dune：PoolFilterService.check_tx_hashes() -> _check_tx_hashes_with_dune()
  该路径由 routes.py 注入 DuneService 触发，是 /api/unipool/check 的实际实现。
- 本地 pool 列表关闭时直接返回错误（"本地池列表已禁用"）。

当前未被使用的内部路径（在 storage=None 且注入 DuneService 时）：
- 本地缓存/SQLite：PoolFilterStorage 及 _resolve_db_path()
- trace 过滤：filter_trace() 及其依赖 _topic_to_address()、_parse_wei_value()
- refresh_pool_set()
- check_tx_hash() 的 BlockSec 提取分支
"""

import asyncio
import os
import sqlite3
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Tuple

from ..config import config
from ..services.extractor import BlockSecExtractor
from ..services.dune_service import DuneService


TOPIC_V3 = "0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67"
TOPIC_V4 = "0x40e9cecb9f5f1f1c5b9c97dec2917b7ee92e57ba5563708daca94dd84ad7112f"
TOPIC_V2 = "0xd78ad95fa46c994b6551d0da85fc275fe613ce37657fb8d5e3d130840159d822"
TOPIC_TRANSFER = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"


def _resolve_db_path(db_path: Optional[str] = None) -> Path:
    if db_path:
        return Path(db_path)
    env_path = os.getenv("POOL_FILTER_DB_PATH")
    if env_path:
        return Path(env_path)
    root = Path(__file__).resolve().parents[3]
    return root / "data" / "unipool.db"


def _normalize_address(value: str) -> str:
    return (value or "").lower()


def _topic_to_address(topic: str) -> str:
    if not topic or not isinstance(topic, str):
        return ""
    cleaned = topic.lower().replace("0x", "")
    if len(cleaned) < 40:
        return ""
    return "0x" + cleaned[-40:]


def _parse_wei_value(value: Optional[str]) -> int:
    if value is None:
        return 0
    if isinstance(value, (int, float)):
        return int(value)
    value_str = str(value).strip()
    if value_str == "":
        return 0
    if value_str.startswith("0x"):
        try:
            return int(value_str, 16)
        except ValueError:
            return 0
    try:
        return int(Decimal(value_str) * Decimal(10 ** 18))
    except (InvalidOperation, ValueError):
        return 0


class PoolFilterStorage:
    def __init__(self, db_path: Optional[str] = None) -> None:
        self._db_path = _resolve_db_path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(str(self._db_path))

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS unipool_address (
                  pool_address TEXT PRIMARY KEY,
                  project TEXT,
                  first_seen_time TEXT
                );
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sync_meta (
                  key TEXT PRIMARY KEY,
                  value TEXT
                );
                """
            )

    def upsert_pools(self, rows: Sequence[Dict[str, str]]) -> None:
        if not rows:
            return
        payload = []
        for row in rows:
            pool_address = _normalize_address(row.get("pool_address", ""))
            if not pool_address:
                continue
            payload.append(
                (
                    pool_address,
                    row.get("project") or "",
                    row.get("first_seen_time") or "",
                )
            )
        if not payload:
            return
        with self._connect() as conn:
            conn.executemany(
                """
                INSERT INTO unipool_address (pool_address, project, first_seen_time)
                VALUES (?, ?, ?)
                ON CONFLICT(pool_address) DO UPDATE SET
                  project=excluded.project,
                  first_seen_time=MIN(unipool_address.first_seen_time, excluded.first_seen_time)
                """,
                payload,
            )

    def load_pool_set(self) -> set[str]:
        with self._connect() as conn:
            rows = conn.execute("SELECT pool_address FROM unipool_address").fetchall()
        return {row[0].lower() for row in rows if row and row[0]}

    def get_pool_count(self) -> int:
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(1) FROM unipool_address").fetchone()
        return int(row[0] or 0) if row else 0

    def get_last_sync_time(self) -> str:
        with self._connect() as conn:
            row = conn.execute("SELECT value FROM sync_meta WHERE key='last_sync_time'").fetchone()
        return row[0] if row else "1970-01-01 00:00:00"

    def set_last_sync_time(self, timestamp: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO sync_meta (key, value)
                VALUES ('last_sync_time', ?)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value
                """,
                (timestamp,),
            )


@dataclass(frozen=True)
class PoolFilterResult:
    tx_hash: str
    success: bool
    has_uni_pool: bool
    matched_pools: List[str]
    error: Optional[str] = None


class PoolFilterService:
    def __init__(
        self,
        storage: Optional[PoolFilterStorage],
        extractor_factory: Callable[[], BlockSecExtractor] = BlockSecExtractor,
        dune_service: Optional[DuneService] = None,
    ) -> None:
        self._storage = storage
        self._extractor_factory = extractor_factory
        self._dune_service = dune_service
        self._pool_set = storage.load_pool_set() if storage else set()

    def refresh_pool_set(self) -> None:
        if self._storage:
            self._pool_set = self._storage.load_pool_set()

    def get_status(self) -> dict:
        if not self._storage:
            return {
                "pool_count": 0,
                "last_sync_time": None,
                "storage": "disabled",
            }
        return {
            "pool_count": self._storage.get_pool_count(),
            "last_sync_time": self._storage.get_last_sync_time(),
        }

    def filter_trace(self, trace_data: dict) -> Tuple[bool, List[str]]:
        if not self._pool_set:
            return False, []
        data_map = trace_data.get("dataMap") or {}
        pool_hits = set()
        asset_flow = False

        for node in data_map.values():
            if node.get("nodeType") != 1:
                continue
            event = node.get("event") or {}
            addr = _normalize_address(event.get("contract", ""))
            topics = event.get("topics") or []
            if addr in self._pool_set:
                pool_hits.add(addr)
            if topics:
                topic0 = topics[0].lower()
                if topic0 == TOPIC_TRANSFER and len(topics) >= 3:
                    from_addr = _topic_to_address(topics[1])
                    to_addr = _topic_to_address(topics[2])
                    if from_addr in self._pool_set:
                        pool_hits.add(from_addr)
                        asset_flow = True
                    if to_addr in self._pool_set:
                        pool_hits.add(to_addr)
                        asset_flow = True
                if topic0 in {TOPIC_V2, TOPIC_V3, TOPIC_V4} and addr in self._pool_set:
                    pool_hits.add(addr)
                    asset_flow = True

        for node in data_map.values():
            inv = node.get("invocation") or {}
            if not inv:
                continue
            to_addr = _normalize_address(inv.get("address", ""))
            from_addr = _normalize_address(inv.get("fromAddress", ""))
            if to_addr in self._pool_set:
                pool_hits.add(to_addr)
            if from_addr in self._pool_set:
                pool_hits.add(from_addr)
            value = _parse_wei_value(inv.get("value"))
            if value > 0 and (to_addr in self._pool_set or from_addr in self._pool_set):
                asset_flow = True

        return bool(pool_hits) and asset_flow, sorted(pool_hits)

    def check_tx_hash(self, tx_hash: str) -> PoolFilterResult:
        if self._dune_service:
            results = self._check_tx_hashes_with_dune([tx_hash])
            return results[0] if results else PoolFilterResult(
                tx_hash=tx_hash,
                success=False,
                has_uni_pool=False,
                matched_pools=[],
                error="Dune 返回空结果",
            )
        extractor = self._extractor_factory()
        try:
            result = asyncio.run(extractor.extract_blocksec_data(tx_hash))
        except Exception as exc:
            return PoolFilterResult(
                tx_hash=tx_hash,
                success=False,
                has_uni_pool=False,
                matched_pools=[],
                error=str(exc),
            )

        if not result or not result.get("success"):
            return PoolFilterResult(
                tx_hash=tx_hash,
                success=False,
                has_uni_pool=False,
                matched_pools=[],
                error=result.get("error", "无法提取交易数据") if result else "无法提取交易数据",
            )

        trace_data = result.get("trace_data") or {}
        has_pool, matched = self.filter_trace(trace_data)
        return PoolFilterResult(
            tx_hash=tx_hash,
            success=True,
            has_uni_pool=has_pool,
            matched_pools=matched,
        )

    def check_tx_hashes(self, tx_hashes: Sequence[str]) -> List[PoolFilterResult]:
        if self._dune_service:
            return self._check_tx_hashes_with_dune(tx_hashes)
        if not self._pool_set:
            return [
                PoolFilterResult(
                    tx_hash=_normalize_address(tx_hash),
                    success=False,
                    has_uni_pool=False,
                    matched_pools=[],
                    error="本地池列表已禁用",
                )
                for tx_hash in tx_hashes
            ]
        results = []
        for tx_hash in tx_hashes:
            results.append(self.check_tx_hash(tx_hash))
        return results

    def _check_tx_hashes_with_dune(self, tx_hashes: Sequence[str]) -> List[PoolFilterResult]:
        results = []
        try:
            dune_rows = self._dune_service.fetch_uniswap_flags(tx_hashes)
        except Exception as exc:
            error_msg = str(exc)
            for tx_hash in tx_hashes:
                results.append(PoolFilterResult(
                    tx_hash=tx_hash,
                    success=False,
                    has_uni_pool=False,
                    matched_pools=[],
                    error=error_msg,
                ))
            return results

        dune_map = {row.tx_hash: row.bool_used_uni for row in dune_rows}
        for raw_hash in tx_hashes:
            tx_hash = _normalize_address(raw_hash)
            results.append(PoolFilterResult(
                tx_hash=tx_hash,
                success=True,
                has_uni_pool=bool(dune_map.get(tx_hash, False)),
                matched_pools=[],
            ))
        return results
