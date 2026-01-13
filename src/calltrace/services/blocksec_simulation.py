"""
BlockSec simulation API client and payload normalization.
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Dict, Optional

import requests

BLOCKSEC_API_BASE = "https://app.blocksec.com/api/v1"
BLOCKSEC_SIMULATION_ENDPOINT = f"{BLOCKSEC_API_BASE}/tx/simulation"
BLOCKSEC_SIM_TRACE_ENDPOINT = f"{BLOCKSEC_API_BASE}/simulation/tx/trace"
BLOCKSEC_SIM_BALANCE_ENDPOINT = f"{BLOCKSEC_API_BASE}/simulation/tx/balance-change"
BLOCKSEC_SIM_BASIC_ENDPOINT = f"{BLOCKSEC_API_BASE}/simulation/tx/basic-info"

CHAIN_ID_MAP = {
    1: "eth",
    56: "bsc",
    137: "polygon",
}


def resolve_chain_name(payload: Dict[str, Any]) -> str:
    chain = payload.get("chain")
    if isinstance(chain, str) and chain:
        return chain
    chain_id = payload.get("chainID") or payload.get("chainId") or payload.get("chain_id")
    if isinstance(chain_id, str) and chain_id.isdigit():
        chain_id = int(chain_id)
    if isinstance(chain_id, int):
        return CHAIN_ID_MAP.get(chain_id, "eth")
    return "eth"


def resolve_cookie_file() -> Path:
    root = Path(__file__).resolve().parents[3]
    cookie_file = os.getenv("BLOCKSEC_COOKIE_FILE", str(root / "blocksec_cookies.json"))
    return Path(cookie_file)


def load_blocksec_cookies(cookie_file: Path) -> dict:
    if not cookie_file.exists():
        raise FileNotFoundError(f"Cookie 文件不存在: {cookie_file}")
    with cookie_file.open() as f:
        cookies = json.load(f)
    if isinstance(cookies, list):
        return {item.get("name"): item.get("value") for item in cookies if item.get("name")}
    if isinstance(cookies, dict):
        return cookies
    raise ValueError("Cookie 文件格式不支持")


def build_blocksec_session(cookie_file: Optional[Path] = None) -> requests.Session:
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Content-Type": "application/json",
        "Origin": "https://app.blocksec.com",
        "Referer": "https://app.blocksec.com/",
    })
    cookie_path = cookie_file or resolve_cookie_file()
    cookies = load_blocksec_cookies(cookie_path)
    for name, value in cookies.items():
        session.cookies.set(name, value, domain=".blocksec.com")
    return session


def post_blocksec_api(session: requests.Session, url: str, payload: dict) -> dict:
    response = session.post(url, json=payload, timeout=60)
    if response.status_code == 403:
        raise PermissionError("API 请求被拒绝 (403)，请更新 BlockSec cookies")
    if response.status_code >= 400:
        detail = response.text.strip()
        message = f"BlockSec API {response.status_code}: {detail}" if detail else f"BlockSec API {response.status_code}"
        raise RuntimeError(message)
    result = response.json()
    if isinstance(result, dict) and result.get("code") not in (None, 0):
        raise RuntimeError(result.get("message", "BlockSec API 错误"))
    if isinstance(result, dict) and "data" in result:
        return result["data"] or {}
    return result if isinstance(result, dict) else {}


def _convert_eth_to_wei(value: object) -> str:
    if value is None:
        raise ValueError("value 不能为空")
    if isinstance(value, (int, float)):
        value = str(value)
    if not isinstance(value, str):
        raise ValueError("value 必须是字符串")
    try:
        eth = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError("value 不是合法的 ETH 数字") from exc
    wei = eth * Decimal("1000000000000000000")
    if wei != wei.to_integral_value():
        raise ValueError("value 精度超过 18 位，无法转换为 wei")
    return str(int(wei))


def normalize_simulation_payload(raw: dict, convert_value: bool = True) -> dict:
    payload = json.loads(json.dumps(raw))
    if not convert_value:
        return payload
    txn_custom = payload.get("txnCustom")
    if isinstance(txn_custom, dict) and "value" in txn_custom:
        txn_custom["value"] = _convert_eth_to_wei(txn_custom["value"])
    elif "value" in payload:
        payload["value"] = _convert_eth_to_wei(payload["value"])
    return payload


def _strip_none(payload: dict) -> dict:
    return {key: value for key, value in payload.items() if value is not None}


def build_simulation_request_payload(raw: dict, convert_value_for_flat: bool = True) -> dict:
    has_txn_custom = isinstance(raw.get("txnCustom"), dict)
    normalized = normalize_simulation_payload(raw, convert_value=convert_value_for_flat and not has_txn_custom)
    chain_id = normalized.get("chainID") or normalized.get("chainId") or normalized.get("chain_id")
    if isinstance(chain_id, str) and chain_id.isdigit():
        chain_id = int(chain_id)
    if not isinstance(chain_id, int):
        chain_id = 1
    txn_custom = normalized.get("txnCustom")
    if isinstance(txn_custom, dict):
        normalized["chainID"] = chain_id
        if normalized.get("simulationType") in (None, ""):
            normalized["simulationType"] = "custom"
        return normalized

    if any(key in normalized for key in ("sender", "receiver", "inputData")):
        payload = {
            "chainID": chain_id,
            "chain": resolve_chain_name(normalized),
            "from": normalized.get("sender") or normalized.get("from"),
            "to": normalized.get("receiver") or normalized.get("to"),
            "data": normalized.get("inputData") or normalized.get("data"),
            "value": normalized.get("value"),
            "gasLimit": str(normalized.get("gasLimit")) if normalized.get("gasLimit") is not None else None,
            "gasPrice": str(normalized.get("gasPrice")) if normalized.get("gasPrice") not in (None, "") else None,
            "blockNumber": normalized.get("blockNumber"),
            "position": normalized.get("position"),
            "simulationType": normalized.get("simulationType"),
        }
        payload = _strip_none(payload)
        if payload.get("simulationType") in (None, ""):
            payload["simulationType"] = 0
        return payload

    if isinstance(chain_id, int):
        normalized["chainID"] = chain_id
    return normalized


def find_trace_payload(payload: object) -> dict:
    if isinstance(payload, dict):
        if "dataMap" in payload and "mainTrace" in payload:
            return payload
        for key in ("data", "result"):
            sub = payload.get(key)
            if isinstance(sub, dict) and "dataMap" in sub and "mainTrace" in sub:
                return sub
    return {}


@dataclass
class SimulationResult:
    simulation_id: Optional[str]
    tx_hash: str
    simulation_url: str
    timestamp_ms: int
    trace_data: Optional[dict] = None
    balance_change: Optional[dict] = None
    basic_info: Optional[dict] = None


def run_simulation_with_payload(
    payload: dict,
    cookie_file: Optional[Path] = None,
    fetch_trace: bool = True,
) -> SimulationResult:
    session = build_blocksec_session(cookie_file)
    sim_data = post_blocksec_api(session, BLOCKSEC_SIMULATION_ENDPOINT, payload)

    simulation_id = (
        sim_data.get("simulationId")
        or sim_data.get("simulationID")
        or sim_data.get("simulation_id")
    )
    tx_hash = sim_data.get("txHash") or sim_data.get("tx_hash") or sim_data.get("hash")
    if not tx_hash:
        keys = ",".join(sorted(sim_data.keys())) if isinstance(sim_data, dict) else ""
        raise RuntimeError(f"模拟响应缺少 txHash (keys={keys})")

    timestamp = int(time.time() * 1000)
    chain_name = resolve_chain_name(payload)
    simulation_url = (
        f"https://app.blocksec.com/explorer/tx/{chain_name}/{tx_hash}"
        f"?event=simulation&type=0&timestamp={timestamp}"
    )

    result = SimulationResult(
        simulation_id=simulation_id,
        tx_hash=tx_hash,
        simulation_url=simulation_url,
        timestamp_ms=timestamp,
    )

    if not simulation_id or not fetch_trace:
        return result

    trace_payload = {"chain": chain_name, "simulationId": simulation_id, "timestamp": timestamp}
    trace_data_raw = post_blocksec_api(session, BLOCKSEC_SIM_TRACE_ENDPOINT, trace_payload)
    result.trace_data = find_trace_payload(trace_data_raw)
    result.balance_change = post_blocksec_api(session, BLOCKSEC_SIM_BALANCE_ENDPOINT, trace_payload)
    result.basic_info = post_blocksec_api(session, BLOCKSEC_SIM_BASIC_ENDPOINT, trace_payload)
    return result


def run_simulation(
    raw_payload: dict,
    cookie_file: Optional[Path] = None,
    convert_value_for_flat: bool = True,
    fetch_trace: bool = True,
) -> SimulationResult:
    payload = build_simulation_request_payload(raw_payload, convert_value_for_flat=convert_value_for_flat)
    return run_simulation_with_payload(payload, cookie_file=cookie_file, fetch_trace=fetch_trace)
