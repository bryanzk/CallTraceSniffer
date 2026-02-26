"""BlockSec parser API adapter.

Routes legacy service-layer calls to remote blocksec-parser HTTP API.
"""

from __future__ import annotations

import os
import re
import time
from urllib.parse import parse_qs, urlparse
from typing import Any

import requests


TX_HASH_RE = re.compile(r"^0x[a-fA-F0-9]{64}$")
DEFAULT_BASE_URL = "http://127.0.0.1:4444"
RETRY_BACKOFF_SECONDS = (1, 2, 4)


def _base_url() -> str:
    return os.getenv("BLOCKSEC_PARSER_API_BASE_URL", DEFAULT_BASE_URL).strip().rstrip("/")


def _normalize_tx_hash(tx_hash: str) -> str:
    candidate = (tx_hash or "").strip()
    if not TX_HASH_RE.fullmatch(candidate):
        raise ValueError(f"非法 tx_hash: {tx_hash}")
    return candidate.lower()


def _validate_strategy(strategy: str) -> str:
    normalized = (strategy or "api").strip().lower()
    if normalized not in {"api", "auto", "playwright"}:
        raise ValueError(f"无效 strategy: {strategy}")
    return normalized


def _request_parse(path: str, payload: dict[str, Any], timeout_sec: int = 45) -> dict[str, Any]:
    url = f"{_base_url()}{path}"
    last_error: Exception | None = None

    for idx, backoff in enumerate(RETRY_BACKOFF_SECONDS):
        should_retry = idx < len(RETRY_BACKOFF_SECONDS) - 1
        try:
            response = requests.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=timeout_sec,
            )
        except requests.Timeout as exc:
            last_error = TimeoutError(f"blocksec-parser API 超时: {url}")
            if should_retry:
                time.sleep(backoff)
                continue
            raise last_error from exc
        except requests.RequestException as exc:
            last_error = RuntimeError(f"blocksec-parser API 请求失败: {url}")
            if should_retry:
                time.sleep(backoff)
                continue
            raise last_error from exc

        if response.status_code in {400, 422}:
            raise ValueError(response.text.strip() or f"请求参数不合法: {url}")
        if response.status_code in {502, 504}:
            last_error = (
                TimeoutError(f"blocksec-parser API 超时(504): {url}")
                if response.status_code == 504
                else RuntimeError(f"blocksec-parser API 错误(502): {url}")
            )
            if should_retry:
                time.sleep(backoff)
                continue
            raise last_error
        if response.status_code >= 500:
            raise RuntimeError(response.text.strip() or f"blocksec-parser API 错误({response.status_code}): {url}")
        if response.status_code != 200:
            raise RuntimeError(f"blocksec-parser API 非预期状态码: {response.status_code}")

        try:
            data = response.json()
        except ValueError as exc:
            raise RuntimeError("blocksec-parser API 响应不是合法 JSON") from exc

        if not isinstance(data, dict):
            raise RuntimeError("blocksec-parser API 响应格式非法")
        return data

    # defensive fallback; loop should already return/raise.
    raise RuntimeError(str(last_error) if last_error else f"blocksec-parser API 请求失败: {url}")


def parse_tx(tx_hash: str, strategy: str = "api", timeout_sec: int = 45) -> dict[str, Any]:
    normalized_hash = _normalize_tx_hash(tx_hash)
    return _request_parse(
        "/v1/parse/tx",
        {"tx_hash": normalized_hash, "strategy": _validate_strategy(strategy)},
        timeout_sec=timeout_sec,
    )


def parse_simulation_url_result(sim_url: str, strategy: str = "api", timeout_sec: int = 45) -> dict[str, Any]:
    parse_simulation_url_tuple(sim_url)
    return _request_parse(
        "/v1/parse/simulation-url",
        {"simulation_url": sim_url, "strategy": _validate_strategy(strategy)},
        timeout_sec=timeout_sec,
    )


def parse_simulation_url_tuple(sim_url: str) -> tuple[str, str]:
    if not sim_url:
        raise ValueError("模拟URL不能为空")
    parsed = urlparse(sim_url)
    if parsed.scheme not in ("http", "https") or "blocksec.com" not in parsed.netloc:
        raise ValueError("无效的BlockSec URL")
    match = re.search(r"/explorer/tx/eth/(0x[a-fA-F0-9]{64})", parsed.path)
    if not match:
        raise ValueError("URL中未找到交易哈希")
    tx_hash = match.group(1).lower()
    query = parse_qs(parsed.query)
    event = query.get("event", [""])[0]
    if event and event != "simulation":
        raise ValueError("URL不是simulation类型")
    return tx_hash, sim_url


def sanitize_payload(raw_payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(raw_payload, dict):
        raise ValueError("BlockSec extractor 返回格式非法")
    if raw_payload.get("success") is False:
        raise ValueError(raw_payload.get("error", "BlockSec extractor 执行失败"))
    cleaned = {
        key: value
        for key, value in raw_payload.items()
        if key not in {"success", "tx_hash", "error"}
    }
    trace_data = cleaned.get("trace_data")
    if not trace_data:
        raise ValueError("BlockSec 数据缺少 trace_data")
    return cleaned


def fetch_payload_via_api(tx_hash: str, timeout_sec: int = 45) -> dict[str, Any]:
    result = parse_tx(tx_hash, strategy="api", timeout_sec=timeout_sec)
    if not result.get("success"):
        raise RuntimeError(result.get("error", "blocksec-parser API 返回失败"))
    clean = result.get("clean")
    if not isinstance(clean, dict) or not clean.get("trace_data"):
        raise RuntimeError("blocksec-parser API 响应缺少 clean.trace_data")
    return clean


def get_playwright_extractor_class() -> type:
    # Backward compatibility for previous adapter-level tests/imports.
    from .extractor import BlockSecExtractor
    return BlockSecExtractor
