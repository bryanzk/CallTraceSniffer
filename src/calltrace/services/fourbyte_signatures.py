"""4byte 方法签名查询与 selector 提取。"""

from __future__ import annotations

import json
import re
from typing import Any, Iterable
from urllib.parse import urlencode
from urllib.request import Request, urlopen

FOURBYTE_SIGNATURES_API = "https://www.4byte.directory/api/v1/signatures/"
SELECTOR_RE = re.compile(r"^(?:0x)?[0-9a-fA-F]{8}$")


def normalize_selector(raw: Any) -> str | None:
    """把 selector 规范化为 0x 前缀的 4-byte 十六进制。"""
    if not isinstance(raw, str):
        return None
    value = raw.strip()
    if not SELECTOR_RE.fullmatch(value):
        return None
    value = value.lower()
    if not value.startswith("0x"):
        value = f"0x{value}"
    return value


def extract_selectors_from_payload(payload: Any, max_count: int = 200) -> list[str]:
    """递归扫描 JSON，提取可能的 selector。"""
    found: set[str] = set()

    def _walk(node: Any) -> None:
        if len(found) >= max_count:
            return
        if isinstance(node, dict):
            for value in node.values():
                _walk(value)
            return
        if isinstance(node, list):
            for item in node:
                _walk(item)
            return
        normalized = normalize_selector(node)
        if normalized:
            found.add(normalized)

    _walk(payload)
    return sorted(found)


def _http_get_json(url: str, timeout_sec: int) -> dict[str, Any]:
    req = Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "CallTraceSniffer/1.0",
        },
        method="GET",
    )
    with urlopen(req, timeout=timeout_sec) as resp:
        raw = resp.read()
    data = json.loads(raw.decode("utf-8"))
    if not isinstance(data, dict):
        return {}
    return data


def lookup_selector_signatures(
    selectors: Iterable[str],
    timeout_sec: int = 12,
    max_per_selector: int = 5,
) -> dict[str, list[str]]:
    """查询 4byte.directory，返回 selector -> text_signature 列表。"""
    mapping: dict[str, list[str]] = {}
    for selector in selectors:
        normalized = normalize_selector(selector)
        if not normalized:
            continue

        params = urlencode({"hex_signature": normalized})
        url = f"{FOURBYTE_SIGNATURES_API}?{params}"
        try:
            payload = _http_get_json(url, timeout_sec=timeout_sec)
        except Exception:
            mapping[normalized] = []
            continue

        results = payload.get("results")
        if not isinstance(results, list):
            mapping[normalized] = []
            continue

        text_sigs: list[str] = []
        for item in results:
            if not isinstance(item, dict):
                continue
            text = item.get("text_signature")
            if isinstance(text, str) and text and text not in text_sigs:
                text_sigs.append(text)
            if len(text_sigs) >= max_per_selector:
                break
        mapping[normalized] = text_sigs

    return mapping


def build_selector_signature_map(
    payload: Any,
    timeout_sec: int = 12,
    max_selectors: int = 200,
    max_per_selector: int = 5,
) -> dict[str, Any]:
    """从交易 JSON 构建 selector 签名映射结果。"""
    selectors = extract_selectors_from_payload(payload, max_count=max_selectors)
    mapping = lookup_selector_signatures(
        selectors,
        timeout_sec=timeout_sec,
        max_per_selector=max_per_selector,
    )
    resolved = sum(1 for x in mapping.values() if x)
    return {
        "selectors_total": len(selectors),
        "selectors_resolved": resolved,
        "mapping": mapping,
    }

