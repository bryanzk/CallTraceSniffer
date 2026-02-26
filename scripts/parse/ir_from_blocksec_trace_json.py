#!/usr/bin/env python3
"""
从已导出的 BlockSec trace JSON 生成 IR V1（BlockSec 口径）。

输入文件期望格式（最少字段）:
{
  "tx_hash": "0x...",
  "trace_data": { "dataMap": {...}, "mainTrace": [...] }
}

输出:
- IR V1 JSON（与服务端 build_blocksec_ir 结构一致）
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from calltrace.services.ir_v1_blocksec import build_blocksec_ir


def _load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("输入 JSON 顶层必须是 object")
    return data


def _resolve_tx_hash(data: Dict[str, Any], fallback: Optional[str]) -> str:
    tx_hash = (data.get("tx_hash") or data.get("txHash") or "").strip()
    if not tx_hash and fallback:
        tx_hash = fallback.strip()
    return tx_hash


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate IR V1 from BlockSec trace JSON")
    parser.add_argument(
        "--input",
        required=True,
        help="输入 trace JSON 文件路径（包含 trace_data）",
    )
    parser.add_argument(
        "--output",
        default="",
        help="输出 IR JSON 文件路径（默认输出到 outputs/<tx_hash>_ir_v1_blocksec.json）",
    )
    parser.add_argument(
        "--tx-hash",
        default="",
        help="可选：手动指定 tx_hash（当输入文件未包含 tx_hash 时使用）",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        raise FileNotFoundError(f"输入文件不存在: {input_path}")

    data = _load_json(input_path)
    trace_data = data.get("trace_data")
    if not isinstance(trace_data, dict):
        raise ValueError("输入 JSON 缺少 trace_data 或 trace_data 不是 object")

    tx_hash = _resolve_tx_hash(data, args.tx_hash)
    if not tx_hash:
        raise ValueError("无法确定 tx_hash（请在输入文件中提供 tx_hash 或使用 --tx-hash）")

    ir = build_blocksec_ir(trace_data, tx_hash=tx_hash, extra={})

    if args.output:
        output_path = Path(args.output)
    else:
        output_path = ROOT / "outputs" / f"{tx_hash}_ir_v1_blocksec.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(ir, f, ensure_ascii=False, indent=2)

    # 轻量校验：确保关键字段存在，便于脚本化使用时快速失败
    if not isinstance(ir, dict) or "rootTrace" not in ir or "tx_hash" not in ir:
        raise RuntimeError("IR 结构异常：缺少 tx_hash/rootTrace")

    print(str(output_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

