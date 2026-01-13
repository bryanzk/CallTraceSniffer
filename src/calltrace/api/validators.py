from __future__ import annotations

from typing import Any, Dict, Optional, Tuple


def parse_json_object(request: Any) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    data = request.get_json(silent=True)
    if data is None:
        return {}, None
    if not isinstance(data, dict):
        return None, "请求体必须为JSON对象"
    return data, None


def validate_tx_hash(data: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
    tx_hash = (data.get("tx_hash") or "").strip()
    if not tx_hash:
        return None, "交易哈希不能为空"
    if not tx_hash.startswith("0x") or len(tx_hash) != 66:
        return None, "无效的交易哈希格式"
    return tx_hash, None


def validate_simulation_url(data: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
    sim_url = (data.get("simulation_url") or "").strip()
    if not sim_url:
        return None, "模拟URL不能为空"
    return sim_url, None
