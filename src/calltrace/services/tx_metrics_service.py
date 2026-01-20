from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_DOWN
import logging
import os
from typing import Any, Dict, Iterable, List, Optional, Tuple

import requests

from ..config import config
from .dune_service import _extract_rows


logger = logging.getLogger(__name__)

WEI = Decimal(10) ** 18


def _normalize_tx_hash(tx_hash: str) -> str:
    return (tx_hash or "").strip().lower()


def _normalize_address(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (bytes, bytearray)):
        return "0x" + value.hex()
    return str(value).strip().lower()


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except Exception:
        return 0


def _parse_decimal(value: Any) -> Optional[Decimal]:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except Exception:
        return None


def _format_decimal(value: Optional[Decimal]) -> Optional[str]:
    if value is None:
        return None
    rendered = format(value, "f")
    if "." in rendered:
        rendered = rendered.rstrip("0").rstrip(".")
    return rendered or "0"


def _eth_to_wei(value: Decimal) -> int:
    return int((value * WEI).quantize(Decimal("1"), rounding=ROUND_DOWN))


def _extract_tx_meta(payload: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    tx_meta = payload.get("txMeta")
    return tx_meta if isinstance(tx_meta, dict) else {}


def _extract_eth_price_usd(payload: Optional[Dict[str, Any]], weth_address: str) -> Optional[Decimal]:
    if not isinstance(payload, dict):
        return None
    for item in payload.get("tokenPrices", []) or []:
        if not isinstance(item, dict):
            continue
        token_spec = str(item.get("tokenSpec") or "").upper()
        token_address = _normalize_address(item.get("tokenAddress"))
        if token_spec == "PLATFORM" or token_address == weth_address:
            price = _parse_decimal(item.get("priceInUsd"))
            if price is not None:
                return price
    return None


def _compute_bot_revenue_wei(
    payload: Optional[Dict[str, Any]],
    bot_address: str,
    weth_address: str,
) -> int:
    if not isinstance(payload, dict) or not bot_address:
        return 0
    bot_address_norm = _normalize_address(bot_address)
    total = 0
    for entry in payload.get("tokenFlows", []) or []:
        if not isinstance(entry, dict):
            continue
        if _normalize_address(entry.get("address")) != bot_address_norm:
            continue
        for balance in entry.get("tokenBalances", []) or []:
            if not isinstance(balance, dict):
                continue
            token_spec = str(balance.get("tokenSpec") or "").upper()
            token_address = _normalize_address(balance.get("tokenAddress"))
            if token_spec == "PLATFORM" or token_address == weth_address:
                total += _safe_int(balance.get("tokenAmount"))
    return total


def _compute_bot_revenue_usd_all(payload: Optional[Dict[str, Any]], bot_address: str) -> Decimal:
    if not isinstance(payload, dict) or not bot_address:
        return Decimal(0)
    bot_address_norm = _normalize_address(bot_address)
    total = Decimal(0)
    for entry in payload.get("tokenFlows", []) or []:
        if not isinstance(entry, dict):
            continue
        if _normalize_address(entry.get("address")) != bot_address_norm:
            continue
        for balance in entry.get("tokenBalances", []) or []:
            if not isinstance(balance, dict):
                continue
            token_volume = balance.get("tokenVolume")
            if token_volume is None:
                continue
            value = _parse_decimal(token_volume)
            if value is not None:
                total += value
    return total


def _normalize_dune_tx_hash(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (bytes, bytearray)):
        return "0x" + value.hex()
    return _normalize_tx_hash(str(value))


def _normalize_builder_name(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, (bytes, bytearray)):
        return "0x" + value.hex()
    text = str(value).strip()
    return text or None


def _build_builder_metrics(
    tx_meta: Dict[str, Any],
    dune_row: Optional[Dict[str, Any]],
    gas_used: int,
) -> Tuple[Optional[int], Optional[int], int]:
    gas_price_raw = tx_meta.get("gasPrice")
    base_fee_raw = tx_meta.get("baseFeePerGas")
    gas_price = _safe_int(gas_price_raw)
    base_fee = _safe_int(base_fee_raw)
    builder_tip_per_gas_wei: Optional[int] = None
    builder_tip_wei: Optional[int] = None

    if gas_used and gas_price_raw is not None and base_fee_raw is not None:
        builder_tip_per_gas_wei = max(0, gas_price - base_fee)
        builder_tip_wei = builder_tip_per_gas_wei * gas_used
    else:
        dune_priority_fee = _parse_decimal(dune_row.get("priority_fee") if dune_row else None)
        dune_builder_rewards = _parse_decimal(dune_row.get("builder_rewards") if dune_row else None)
        dune_miner_tip = _parse_decimal(dune_row.get("miner_tip_amount") if dune_row else None)
        if dune_miner_tip is None:
            dune_miner_tip = Decimal(0)
        if dune_priority_fee is not None:
            builder_tip_wei = _eth_to_wei(dune_priority_fee)
        elif dune_builder_rewards is not None:
            builder_tip_wei = _eth_to_wei(dune_builder_rewards) - _eth_to_wei(dune_miner_tip)

        if builder_tip_wei is not None and gas_used:
            builder_tip_per_gas_wei = builder_tip_wei // gas_used

    return builder_tip_wei, builder_tip_per_gas_wei, gas_used


@dataclass(frozen=True)
class EigenPhiClient:
    base_url: str = config.EIGENPHI_BASE_URL
    timeout_ms: int = config.REQUEST_TIMEOUT
    session: Optional[requests.Session] = None

    def fetch_tx(self, tx_hash: str) -> Optional[Dict[str, Any]]:
        url = self.base_url.format(tx_hash=tx_hash)
        session = self.session or requests.Session()
        try:
            response = session.get(url, timeout=self.timeout_ms / 1000)
            response.raise_for_status()
        except Exception as exc:
            logger.warning("EigenPhi 请求失败: %s", exc)
            return None
        try:
            payload = response.json()
        except Exception:
            return None
        return payload if isinstance(payload, dict) else None


@dataclass(frozen=True)
class RpcClient:
    rpc_url: str = config.ETH_RPC_URL
    timeout_ms: int = config.REQUEST_TIMEOUT
    session: Optional[requests.Session] = None

    def get_block_tx_count(self, block_number: int) -> Optional[int]:
        if not self.rpc_url:
            return None
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "eth_getBlockByNumber",
            "params": [hex(block_number), False],
        }
        session = self.session or requests.Session()
        try:
            response = session.post(self.rpc_url, json=payload, timeout=self.timeout_ms / 1000)
            response.raise_for_status()
        except Exception as exc:
            logger.warning("RPC 请求失败: %s", exc)
            return None
        try:
            data = response.json()
        except Exception:
            return None
        result = data.get("result") if isinstance(data, dict) else None
        if not isinstance(result, dict):
            return None
        transactions = result.get("transactions")
        if not isinstance(transactions, list):
            return None
        return len(transactions)


class DuneTxMetricsClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        query_id: int = config.DUNE_TX_QUERY_ID,
        client_factory: Optional[Any] = None,
        performance: Optional[str] = None,
    ) -> None:
        api_key = (api_key or os.getenv("DUNE_API_KEY") or "").strip()
        if not api_key:
            raise ValueError("DUNE_API_KEY is required")
        if client_factory is None:
            from dune_client.client import DuneClient
            client_factory = DuneClient
        self._client = client_factory(api_key)
        self._query_id = query_id
        self._performance = performance or os.getenv("DUNE_QUERY_PERFORMANCE", "").strip() or None

    @staticmethod
    def _format_tx_hashes_param(tx_hashes: Iterable[str]) -> str:
        cleaned = []
        seen = set()
        for raw in tx_hashes:
            tx_hash = _normalize_tx_hash(raw)
            if tx_hash.startswith("0x") and len(tx_hash) == 66 and tx_hash not in seen:
                seen.add(tx_hash)
                cleaned.append(tx_hash)
        return ",".join(cleaned)

    def fetch_rows(self, block_start: int, block_end: int, tx_hashes: Iterable[str]) -> List[Dict[str, Any]]:
        from dune_client.types import QueryParameter
        from dune_client.query import QueryBase

        tx_hashes_param = self._format_tx_hashes_param(tx_hashes)
        query = QueryBase(
            name="tx_metrics",
            query_id=self._query_id,
            params=[
                QueryParameter.number_type(name="block_start", value=block_start),
                QueryParameter.number_type(name="block_end", value=block_end),
                QueryParameter.text_type(name="tx_hashes", value=tx_hashes_param),
            ],
        )
        if self._performance:
            result = self._client.run_query(query=query, performance=self._performance)
        else:
            result = self._client.run_query(query=query)
        return _extract_rows(result)


class TxMetricsService:
    def __init__(
        self,
        eigenphi_client: EigenPhiClient,
        dune_client: DuneTxMetricsClient,
        rpc_client: RpcClient,
    ) -> None:
        self._eigenphi_client = eigenphi_client
        self._dune_client = dune_client
        self._rpc_client = rpc_client

    @classmethod
    def from_config(cls) -> "TxMetricsService":
        if not config.ETH_RPC_URL:
            raise ValueError("ETH_RPC_URL is required")
        eigenphi_client = EigenPhiClient()
        dune_client = DuneTxMetricsClient()
        rpc_client = RpcClient()
        return cls(eigenphi_client, dune_client, rpc_client)

    def analyze_batch(self, tx_hashes: List[str]) -> Dict[str, Any]:
        eigenphi_payloads: Dict[str, Dict[str, Any]] = {}
        failures: Dict[str, str] = {}
        for tx_hash in tx_hashes:
            payload = self._eigenphi_client.fetch_tx(tx_hash)
            if not payload:
                failures[tx_hash] = "EigenPhi 获取失败"
                continue
            eigenphi_payloads[tx_hash] = payload

        block_numbers = []
        for payload in eigenphi_payloads.values():
            tx_meta = _extract_tx_meta(payload)
            block_number = _safe_int(tx_meta.get("blockNumber"))
            if block_number:
                block_numbers.append(block_number)

        if not block_numbers:
            return {
                "ok": False,
                "error": "未获取到有效的 blockNumber",
                "results": [],
            }

        block_start = min(block_numbers)
        block_end = max(block_numbers)

        dune_rows = self._dune_client.fetch_rows(block_start, block_end, tx_hashes)
        dune_map = {_normalize_dune_tx_hash(row.get("tx_hash")): row for row in dune_rows}

        block_tx_count_cache: Dict[int, Optional[int]] = {}
        results = []
        for tx_hash in tx_hashes:
            eigenphi_payload = eigenphi_payloads.get(tx_hash)
            dune_row = dune_map.get(_normalize_tx_hash(tx_hash))
            if not eigenphi_payload and not dune_row:
                results.append({
                    "tx_hash": tx_hash,
                    "success": False,
                    "error": failures.get(tx_hash, "未找到数据"),
                })
                continue

            tx_meta = _extract_tx_meta(eigenphi_payload)
            block_number = _safe_int(tx_meta.get("blockNumber"))
            gas_used = _safe_int(tx_meta.get("gasUsed"))
            block_index = _safe_int(tx_meta.get("transactionIndex"))
            bot_address = _normalize_address(tx_meta.get("transactionToAddress"))
            builder_address = _normalize_address(dune_row.get("builder_address") if dune_row else None)
            if not builder_address:
                builder_address = _normalize_address(tx_meta.get("blockMiner"))
            builder_name = _normalize_builder_name(dune_row.get("builder") if dune_row else None)

            if block_number and block_number not in block_tx_count_cache:
                block_tx_count_cache[block_number] = self._rpc_client.get_block_tx_count(block_number)
            block_tx_count = block_tx_count_cache.get(block_number)

            builder_tip_wei, builder_tip_per_gas_wei, _ = _build_builder_metrics(
                tx_meta, dune_row, gas_used
            )
            miner_tip_amount = _parse_decimal(dune_row.get("miner_tip_amount") if dune_row else None)
            if miner_tip_amount is None:
                miner_tip_amount = Decimal(0)
            coinbase_transfer_wei = _eth_to_wei(miner_tip_amount)
            builder_tip_with_ct_wei = (
                builder_tip_wei + coinbase_transfer_wei if builder_tip_wei is not None else None
            )

            builder_tip_eth = Decimal(builder_tip_wei) / WEI if builder_tip_wei is not None else None
            builder_tip_per_gas_eth = (
                Decimal(builder_tip_per_gas_wei) / WEI if builder_tip_per_gas_wei is not None else None
            )
            coinbase_transfer_eth = Decimal(coinbase_transfer_wei) / WEI
            builder_tip_with_ct_eth = (
                Decimal(builder_tip_with_ct_wei) / WEI if builder_tip_with_ct_wei is not None else None
            )

            revenue_wei = _compute_bot_revenue_wei(eigenphi_payload, bot_address, config.WETH.lower())
            revenue_eth = Decimal(revenue_wei) / WEI
            eth_price_usd = _extract_eth_price_usd(eigenphi_payload, config.WETH.lower())
            revenue_usd = revenue_eth * eth_price_usd if eth_price_usd is not None else None
            revenue_usd_all = _compute_bot_revenue_usd_all(eigenphi_payload, bot_address)

            results.append({
                "tx_hash": tx_hash,
                "success": True,
                "blockNumber": block_number or None,
                "gasUsed": gas_used or None,
                "builderTip": _format_decimal(builder_tip_eth),
                "builderTipPerGas": _format_decimal(builder_tip_per_gas_eth),
                "coinbaseTransfer": _format_decimal(coinbase_transfer_eth),
                "builderTipWithCT": _format_decimal(builder_tip_with_ct_eth),
                "blockIndex": block_index or None,
                "botAddress": bot_address or None,
                "builder": {
                    "address": builder_address or None,
                    "name": builder_name or None,
                },
                "revenueEth": _format_decimal(revenue_eth),
                "revenueUsd": _format_decimal(revenue_usd),
                "revenueUsdAll": _format_decimal(revenue_usd_all),
                "blockTxCount": block_tx_count,
            })

        return {
            "ok": True,
            "block_start": block_start,
            "block_end": block_end,
            "results": results,
        }
