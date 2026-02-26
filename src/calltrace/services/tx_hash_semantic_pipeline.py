"""按 tx hash 拉取三源数据并生成业务语义树。"""

from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .openai_shell_semantic_mvp import (
    DEFAULT_ALLOWED_COMMAND_PREFIXES,
    build_semantic_prompt,
    generate_semantic_tree_with_shell,
)
from .fourbyte_signatures import build_selector_signature_map

EIGENPHI_JSON_URL_TEMPLATE = (
    "https://eigenphi.io/api/v1/analyseTransaction"
    "?chain=ALL&enableCallStack=on&tx={tx_hash}"
)
EIGENPHI_SVG_URL_TEMPLATE = (
    "https://tx.eigenphi.io/analyseTransaction.svg"
    "?chain=ethereum&tx={tx_hash}&rankdir=LR"
)
TX_HASH_RE = re.compile(r"^0x[a-fA-F0-9]{64}$")
MULTIMODAL_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}
BLOCKSEC_ONCHAIN_BASE_URL = "https://app.blocksec.com/api/v1/onchain/tx"
BLOCKSEC_ONCHAIN_ENDPOINTS = {
    "trace_data": "trace",
    "fundflow": "fundflow",
    "balance_change": "balance-change",
    "token_info": "token-info",
    "address_label": "address-label",
    "basic_info": "basic-info",
    "gas_flame": "gas-flame",
}


@dataclass(frozen=True)
class ArtifactPaths:
    """流水线产物路径集合。"""

    base_dir: Path
    eigenphi_json: Path
    blocksec_json: Path
    eigenphi_svg: Path
    selector_signatures_json: Path
    semantic_markdown: Path


def normalize_tx_hash(tx_hash: str) -> str:
    """校验 tx hash 并统一为小写。"""
    candidate = (tx_hash or "").strip()
    if not TX_HASH_RE.fullmatch(candidate):
        raise ValueError(f"非法 tx_hash: {tx_hash}")
    return candidate.lower()


def build_eigenphi_json_url(tx_hash: str) -> str:
    """构造 EigenPhi JSON 接口 URL。"""
    return EIGENPHI_JSON_URL_TEMPLATE.format(tx_hash=normalize_tx_hash(tx_hash))


def build_eigenphi_svg_url(tx_hash: str) -> str:
    """构造 EigenPhi SVG URL。"""
    return EIGENPHI_SVG_URL_TEMPLATE.format(tx_hash=normalize_tx_hash(tx_hash))


def build_artifact_paths(output_root: Path | str, tx_hash: str) -> ArtifactPaths:
    """根据 tx hash 生成标准输出文件路径。"""
    normalized_hash = normalize_tx_hash(tx_hash)
    root = Path(output_root)
    base = root / normalized_hash
    return ArtifactPaths(
        base_dir=base,
        eigenphi_json=base / f"{normalized_hash}_eigenphi.json",
        blocksec_json=base / f"{normalized_hash}_blocksec.json",
        eigenphi_svg=base / f"{normalized_hash}.svg",
        selector_signatures_json=base / "selector_signatures_4byte.json",
        semantic_markdown=base / "semantic_tree_openai_shell_mvp.md",
    )


def choose_multimodal_image_path(reference_image_path: Path | str) -> str | None:
    """只对支持的栅格图片启用 input_image，多余格式走 shell 读取。"""
    path = Path(reference_image_path)
    if path.suffix.lower() in MULTIMODAL_IMAGE_SUFFIXES:
        return str(path)
    return None


def load_env_from_dotenv_if_missing(dotenv_path: Path | str) -> None:
    """从 .env 补充缺失环境变量，不覆盖已有值。"""
    path = Path(dotenv_path)
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'\"")
        if key and key not in os.environ:
            os.environ[key] = value


def sanitize_blocksec_payload(raw_payload: dict[str, Any]) -> dict[str, Any]:
    """清洗 BlockSec extractor 返回值，只保留业务载荷字段。"""
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


def _find_trace_payload(payload: object) -> dict[str, Any] | None:
    if isinstance(payload, dict):
        if "dataMap" in payload and "mainTrace" in payload:
            return payload
        for key in ("data", "result"):
            sub = payload.get(key)
            if isinstance(sub, dict) and "dataMap" in sub and "mainTrace" in sub:
                return sub
    return None


def _unwrap_payload(payload: object) -> object:
    if isinstance(payload, dict):
        for key in ("data", "result"):
            if key in payload:
                return payload[key]
    return payload


def _build_blocksec_cookie_header() -> str | None:
    direct_cookie = os.getenv("BLOCKSEC_COOKIE", "").strip()
    if direct_cookie:
        return direct_cookie

    cookie_file = os.getenv("BLOCKSEC_COOKIE_FILE", "").strip()
    if not cookie_file:
        return None
    path = Path(cookie_file)
    if not path.exists():
        return None
    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        return None

    try:
        loaded = json.loads(raw)
    except json.JSONDecodeError:
        return raw

    if isinstance(loaded, list):
        parts: list[str] = []
        for item in loaded:
            if isinstance(item, dict) and item.get("name") and item.get("value"):
                parts.append(f"{item['name']}={item['value']}")
        return "; ".join(parts) if parts else None
    if isinstance(loaded, dict):
        parts = [f"{k}={v}" for k, v in loaded.items() if k and v is not None]
        return "; ".join(parts) if parts else None
    return None


def _post_json(url: str, payload: dict[str, Any], headers: dict[str, str], timeout_sec: int) -> Any:
    data = json.dumps(payload).encode("utf-8")
    req = Request(url, data=data, headers=headers, method="POST")
    try:
        with urlopen(req, timeout=timeout_sec) as resp:
            raw = resp.read()
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        raise RuntimeError(f"BlockSec API {exc.code}: {detail.strip()}") from exc
    except URLError as exc:
        raise RuntimeError(f"BlockSec API 请求失败: {url}") from exc
    return json.loads(raw.decode("utf-8"))


def fetch_blocksec_payload_via_api(tx_hash: str, timeout_sec: int = 45) -> dict[str, Any]:
    """回退方案：直接调用 BlockSec onchain/tx 接口。"""
    normalized_hash = normalize_tx_hash(tx_hash)
    headers = {
        "accept": "application/json",
        "content-type": "application/json;charset=utf-8",
        "origin": "https://app.blocksec.com",
        "referer": f"https://app.blocksec.com/explorer/tx/eth/{normalized_hash}",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
    }
    cookie = _build_blocksec_cookie_header()
    if cookie:
        headers["cookie"] = cookie

    post_payload = {"chainID": 1, "txnHash": normalized_hash, "blocked": False}
    collected: dict[str, Any] = {}
    for payload_key, endpoint in BLOCKSEC_ONCHAIN_ENDPOINTS.items():
        url = f"{BLOCKSEC_ONCHAIN_BASE_URL}/{endpoint}"
        response = _post_json(url, post_payload, headers, timeout_sec=timeout_sec)
        if payload_key == "trace_data":
            trace_data = _find_trace_payload(response)
            if trace_data is None:
                raise RuntimeError("BlockSec API 响应缺少 trace_data")
            collected[payload_key] = trace_data
            continue
        collected[payload_key] = _unwrap_payload(response)
    return collected


def _http_get_bytes(url: str, timeout_sec: int) -> bytes:
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
        "Accept": "*/*",
    }
    req = Request(url, headers=headers, method="GET")
    try:
        with urlopen(req, timeout=timeout_sec) as resp:
            return resp.read()
    except HTTPError as exc:
        raise RuntimeError(f"HTTP {exc.code}: {url}") from exc
    except URLError as exc:
        raise RuntimeError(f"网络请求失败: {url}") from exc


def download_eigenphi_json(tx_hash: str, output_path: Path, timeout_sec: int = 45) -> dict[str, Any]:
    """下载 EigenPhi analyseTransaction JSON 并落盘。"""
    url = build_eigenphi_json_url(tx_hash)
    raw = _http_get_bytes(url, timeout_sec=timeout_sec)
    try:
        payload = json.loads(raw.decode("utf-8"))
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("EigenPhi JSON 解析失败") from exc

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def download_eigenphi_svg(tx_hash: str, output_path: Path, timeout_sec: int = 45) -> bytes:
    """下载 EigenPhi SVG 并落盘。"""
    url = build_eigenphi_svg_url(tx_hash)
    raw = _http_get_bytes(url, timeout_sec=timeout_sec)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(raw)
    return raw


def extract_blocksec_payload(tx_hash: str) -> dict[str, Any]:
    """调用代码中的 BlockSec extractor 获取交易数据。"""
    extractor_error: Exception | None = None
    try:
        from .extractor import BlockSecExtractor
        extractor = BlockSecExtractor()
        result = asyncio.run(extractor.extract_blocksec_data(normalize_tx_hash(tx_hash)))
        if isinstance(result, dict) and result.get("trace_data"):
            return result
        extractor_error = RuntimeError("BlockSecExtractor 未返回 trace_data")
    except Exception as exc:  # pragma: no cover
        extractor_error = exc

    try:
        return fetch_blocksec_payload_via_api(tx_hash)
    except Exception as api_exc:  # pragma: no cover
        if extractor_error is not None:
            raise RuntimeError(
                "BlockSecExtractor 与 API 回退均失败。"
                f" extractor_error={extractor_error}; api_error={api_exc}"
            ) from api_exc
        raise


def generate_semantic_markdown(
    *,
    eigenphi_json_path: Path,
    blocksec_json_path: Path,
    rule_json_path: Path,
    reference_image_path: Path,
    output_markdown_path: Path,
    selector_signatures_path: Path | None,
    model: str,
    max_turns: int,
    workdir: Path,
) -> str:
    """调用 OpenAI Shell MVP 生成业务语义树 Markdown。"""
    try:
        from openai import OpenAI
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            "需要先安装 openai 包。建议使用项目虚拟环境："
            ".run_venv/bin/python -m pip install openai"
        ) from exc

    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("缺少 OPENAI_API_KEY（可放在 .env 或环境变量）")

    prompt = build_semantic_prompt(
        eigenphi_json_path=str(eigenphi_json_path),
        blocksec_json_path=str(blocksec_json_path),
        rule_json_path=str(rule_json_path),
        reference_image_path=str(reference_image_path),
        output_markdown_path=str(output_markdown_path),
    )
    if selector_signatures_path:
        prompt = (
            f"{prompt}\n"
            "补充输入（ABI/方法签名）:\n"
            f"- 4byte selector 映射文件: {selector_signatures_path}\n"
            "读取时优先使用其中的 text_signature 解释 selector 语义。\n"
        )
    multimodal_image_path = choose_multimodal_image_path(reference_image_path)

    client = OpenAI()
    return generate_semantic_tree_with_shell(
        client=client,
        model=model,
        prompt=prompt,
        reference_image_path=multimodal_image_path,
        cwd=str(workdir),
        max_turns=max_turns,
        allowed_prefixes=DEFAULT_ALLOWED_COMMAND_PREFIXES,
    )


def run_pipeline(
    *,
    tx_hash: str,
    output_root: Path,
    rule_json_path: Path,
    model: str,
    max_turns: int,
    timeout_sec: int,
    workdir: Path,
) -> ArtifactPaths:
    """执行完整流程：拉取三源数据并生成语义树。"""
    normalized_hash = normalize_tx_hash(tx_hash)
    if not rule_json_path.exists():
        raise FileNotFoundError(f"rule json not found: {rule_json_path}")

    artifacts = build_artifact_paths(output_root, normalized_hash)
    artifacts.base_dir.mkdir(parents=True, exist_ok=True)

    eigenphi_payload = download_eigenphi_json(normalized_hash, artifacts.eigenphi_json, timeout_sec=timeout_sec)
    selector_signatures = build_selector_signature_map(
        eigenphi_payload,
        timeout_sec=min(15, timeout_sec),
        max_selectors=240,
        max_per_selector=5,
    )
    artifacts.selector_signatures_json.write_text(
        json.dumps(selector_signatures, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    download_eigenphi_svg(normalized_hash, artifacts.eigenphi_svg, timeout_sec=timeout_sec)

    blocksec_raw = extract_blocksec_payload(normalized_hash)
    blocksec_payload = sanitize_blocksec_payload(blocksec_raw)
    artifacts.blocksec_json.write_text(
        json.dumps(blocksec_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    markdown = generate_semantic_markdown(
        eigenphi_json_path=artifacts.eigenphi_json,
        blocksec_json_path=artifacts.blocksec_json,
        rule_json_path=rule_json_path,
        reference_image_path=artifacts.eigenphi_svg,
        output_markdown_path=artifacts.semantic_markdown,
        selector_signatures_path=artifacts.selector_signatures_json,
        model=model,
        max_turns=max_turns,
        workdir=workdir,
    )
    artifacts.semantic_markdown.write_text(markdown, encoding="utf-8")
    return artifacts
