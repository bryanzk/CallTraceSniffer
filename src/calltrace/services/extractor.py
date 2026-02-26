"""BlockSec extraction compatibility wrapper via blocksec-parser API."""

from __future__ import annotations

import re
from typing import Any, Dict, Optional, Tuple

from .blocksec_adapter import (
    parse_simulation_url_result,
    parse_simulation_url_tuple,
    parse_tx,
)


class BlockSecExtractor:
    """BlockSec data extractor with legacy interface compatibility."""

    _ENDPOINT_PAYLOAD_KEYS = {
        "fundflow": "fundflow",
        "balance-change": "balance_change",
        "token-info": "token_info",
        "address-label": "address_label",
        "basic-info": "basic_info",
        "gas-flame": "gas_flame",
        "attack-event": "attack_event",
        "top-profit-loss": "top_profit_loss",
        "state-change": "state_change",
    }

    @staticmethod
    def parse_simulation_url(sim_url: str) -> Tuple[str, str]:
        return parse_simulation_url_tuple(sim_url)

    @staticmethod
    def _find_trace_payload(payload: object) -> Optional[Dict]:
        if isinstance(payload, dict):
            if "dataMap" in payload and "mainTrace" in payload:
                return payload
            for key in ("data", "result"):
                sub = payload.get(key)
                if isinstance(sub, dict) and "dataMap" in sub and "mainTrace" in sub:
                    return sub
        return None

    @staticmethod
    def _unwrap_payload(payload: object) -> object:
        if isinstance(payload, dict):
            for key in ("data", "result"):
                if key in payload:
                    return payload[key]
        return payload

    @classmethod
    def _update_payloads_from_response(cls, url: str, payload: object, collected: Dict[str, Any]) -> None:
        trace = cls._find_trace_payload(payload)
        if trace:
            collected["trace_data"] = trace
            return
        for marker, key in cls._ENDPOINT_PAYLOAD_KEYS.items():
            if marker in url:
                collected[key] = cls._unwrap_payload(payload)
                return

    async def _extract_trace_from_page(self, url: str) -> Optional[Dict]:
        # Keep async signature for backward compatibility with callers/tests.
        tx_match = re.search(r"/explorer/tx/eth/(0x[a-fA-F0-9]{64})", url)
        if tx_match and "event=simulation" not in url:
            result = parse_tx(tx_match.group(1), strategy="api")
        else:
            result = parse_simulation_url_result(url, strategy="api")

        if not isinstance(result, dict):
            return None

        if result.get("success"):
            clean = result.get("clean")
            if isinstance(clean, dict):
                return clean
        return None

    async def extract_blocksec_data(self, tx_hash: str) -> Optional[Dict]:
        """提取 BlockSec 数据。"""
        url = f"https://app.blocksec.com/explorer/tx/eth/{tx_hash}/"
        payloads = await self._extract_trace_from_page(url) or {}
        trace_data = payloads.get("trace_data")
        if trace_data:
            return {
                "success": True,
                "tx_hash": tx_hash,
                **payloads,
            }
        return {
            "success": False,
            "tx_hash": tx_hash,
            "error": "未找到trace数据",
        }

    async def extract_blocksec_simulation_data(self, sim_url: str) -> Optional[Dict]:
        """提取 BlockSec 模拟交易数据。"""
        tx_hash, normalized_url = self.parse_simulation_url(sim_url)
        payloads = await self._extract_trace_from_page(normalized_url) or {}
        trace_data = payloads.get("trace_data")
        if trace_data:
            return {
                "success": True,
                "tx_hash": tx_hash,
                **payloads,
            }
        return {
            "success": False,
            "tx_hash": tx_hash,
            "error": "未找到simulation trace数据",
        }


__all__ = ["BlockSecExtractor"]
