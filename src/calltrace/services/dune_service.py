from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, List, Optional


logger = logging.getLogger(__name__)


def _normalize_tx_hash(tx_hash: str) -> str:
    return (tx_hash or "").strip().lower()


def _format_values_param(tx_hashes: Iterable[str]) -> str:
    items = []
    seen = set()
    for raw in tx_hashes:
        tx_hash = _normalize_tx_hash(raw)
        if tx_hash.startswith("0x") and len(tx_hash) == 66 and tx_hash not in seen:
            seen.add(tx_hash)
            items.append(f"({tx_hash})")
    return ",".join(items)


def _extract_rows(payload: Any) -> List[Dict[str, Any]]:
    if not payload:
        return []
    if hasattr(payload, "result"):
        try:
            return _extract_rows(getattr(payload, "result"))
        except Exception:
            return []
    if hasattr(payload, "rows"):
        try:
            rows = getattr(payload, "rows")
            return rows if isinstance(rows, list) else []
        except Exception:
            return []
    if hasattr(payload, "model_dump"):
        try:
            return _extract_rows(payload.model_dump())
        except Exception:
            return []
    if hasattr(payload, "dict"):
        try:
            return _extract_rows(payload.dict())
        except Exception:
            return []
    if isinstance(payload, dict):
        if "rows" in payload and isinstance(payload["rows"], list):
            return payload["rows"]
        result = payload.get("result")
        if isinstance(result, dict) and isinstance(result.get("rows"), list):
            return result["rows"]
        data = payload.get("data")
        if isinstance(data, dict):
            return _extract_rows(data)
    return []


@dataclass(frozen=True)
class DuneQueryResult:
    tx_hash: str
    bool_used_uni: bool


class DuneService:
    def __init__(
        self,
        api_key: Optional[str] = None,
        query_id: int = 6561637,
        client_factory: Optional[Callable[[str], Any]] = None,
    ) -> None:
        self._api_key = (api_key or os.getenv("DUNE_API_KEY") or "").strip()
        if not self._api_key:
            raise ValueError("DUNE_API_KEY is required")

        if client_factory is None:
            from dune_client.client import DuneClient
            client_factory = DuneClient

        self._client = client_factory(self._api_key)
        self._query_id = query_id

    def get_latest_result(self, params: Optional[Dict[str, Any]] = None) -> Any:
        if params:
            try:
                return self._client.get_latest_result(self._query_id, params=params)
            except TypeError:
                return self._client.get_latest_result(self._query_id)
        return self._client.get_latest_result(self._query_id)

    def fetch_uniswap_flags(self, tx_hashes: Iterable[str]) -> List[DuneQueryResult]:
        values_param = _format_values_param(tx_hashes)
        if not values_param:
            return []
        logger.debug(
            "Dune query %s params tx_hashes=%s",
            self._query_id,
            values_param,
        )
        payload = self.get_latest_result(params={"tx_hashes": values_param})
        logger.debug(
            "Dune query %s payload type=%s keys=%s",
            self._query_id,
            type(payload).__name__,
            sorted(payload.keys()) if isinstance(payload, dict) else None,
        )
        rows = _extract_rows(payload)
        logger.debug(
            "Dune query %s rows=%s sample=%s",
            self._query_id,
            len(rows),
            rows[0] if rows else None,
        )
        results = []
        for row in rows:
            tx_hash = _normalize_tx_hash(str(row.get("tx_hash", "")))
            if not tx_hash:
                continue
            bool_used_uni = bool(row.get("bool_used_uni"))
            results.append(DuneQueryResult(tx_hash=tx_hash, bool_used_uni=bool_used_uni))
        return results
