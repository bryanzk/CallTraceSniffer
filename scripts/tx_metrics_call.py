#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path

import requests


def _load_tx_hashes_from_file(path: Path) -> list[str]:
    content = path.read_text(encoding="utf-8")
    items = []
    for raw in content.replace(",", "\n").splitlines():
        value = raw.strip()
        if value:
            items.append(value)
    return items


def _normalize_tx_hashes(values: list[str]) -> list[str]:
    cleaned = []
    seen = set()
    for raw in values:
        tx_hash = (raw or "").strip()
        if not tx_hash:
            continue
        if not tx_hash.startswith("0x") or len(tx_hash) != 66:
            raise ValueError(f"无效的交易哈希格式: {tx_hash}")
        if tx_hash not in seen:
            seen.add(tx_hash)
            cleaned.append(tx_hash)
    return cleaned


def main() -> int:
    parser = argparse.ArgumentParser(description="调用 /api/tx-metrics-batch 获取交易指标")
    parser.add_argument("--url", default="http://localhost:5001/api/tx-metrics-batch")
    parser.add_argument("--tx-hash", action="append", default=[], help="交易哈希（可重复传入）")
    parser.add_argument("--file", type=Path, help="从文件读取交易哈希（支持换行或逗号分隔）")
    parser.add_argument("--timeout", type=int, default=60, help="请求超时时间（秒）")
    parser.add_argument("--pretty", action="store_true", help="格式化输出 JSON")
    args = parser.parse_args()

    tx_hashes = list(args.tx_hash)
    if args.file:
        if not args.file.exists():
            raise SystemExit(f"文件不存在: {args.file}")
        tx_hashes.extend(_load_tx_hashes_from_file(args.file))

    tx_hashes = _normalize_tx_hashes(tx_hashes)
    if not tx_hashes:
        raise SystemExit("必须提供至少一个 tx_hash")

    response = requests.post(
        args.url,
        json={"tx_hashes": tx_hashes},
        timeout=args.timeout,
    )
    response.raise_for_status()
    payload = response.json()
    if args.pretty:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
