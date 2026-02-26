#!/usr/bin/env python3
"""
批量导出交易的 BlockSec 与 EigenPhi (EigenTx) JSON。

用法:
  # 从 CSV 文件读取（支持 rank,tx_hash,novelty_score,eigentx_url 格式）
  python export_blocksec_eigenphi_batch.py --csv txs.csv -o output/

  # 从命令行传入 tx_hash 列表
  python export_blocksec_eigenphi_batch.py -o output/ 0x78e9fc... 0x45843d...

  # 仅导出 EigenPhi（BlockSec 需 BLOCKSEC_COOKIE 或 BLOCKSEC_COOKIE_FILE）
  python export_blocksec_eigenphi_batch.py --eigenphi-only -o output/ 0x78e9fc...

说明:
  - EigenPhi: 公开 API，无需鉴权
  - BlockSec: 需设置 BLOCKSEC_COOKIE 或 BLOCKSEC_COOKIE_FILE（见 .env 或 docs/development/EXTERNAL_DEPENDENCIES.md）
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from calltrace.services.tx_hash_semantic_pipeline import (  # noqa: E402
    download_eigenphi_json,
    extract_blocksec_payload,
    load_env_from_dotenv_if_missing,
    normalize_tx_hash,
    sanitize_blocksec_payload,
)


def parse_csv_tx_hashes(csv_path: Path) -> list[str]:
    """从 CSV 解析 tx_hash 列。支持 rank,tx_hash,novelty_score,eigentx_url 格式。"""
    hashes: list[str] = []
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            tx_hash = (row.get("tx_hash") or "").strip().strip('"')
            if tx_hash and tx_hash.startswith("0x"):
                hashes.append(tx_hash)
    return hashes


def export_one(
    tx_hash: str,
    output_dir: Path,
    eigenphi_only: bool,
    timeout_sec: int,
) -> dict[str, str | None]:
    """导出单笔交易的 BlockSec 与 EigenPhi JSON。返回各文件路径或 None（失败时）。"""
    norm = normalize_tx_hash(tx_hash)
    base = output_dir / norm
    result: dict[str, str | None] = {
        "tx_hash": norm,
        "eigenphi_json": None,
        "blocksec_json": None,
    }

    # EigenPhi
    eigenphi_path = base / f"{norm}_eigenphi.json"
    try:
        base.mkdir(parents=True, exist_ok=True)
        download_eigenphi_json(norm, eigenphi_path, timeout_sec=timeout_sec)
        result["eigenphi_json"] = str(eigenphi_path)
    except Exception as e:
        print(f"  [EigenPhi] {norm}: {e}", file=sys.stderr)
        return result

    if eigenphi_only:
        return result

    # BlockSec
    blocksec_path = base / f"{norm}_blocksec.json"
    try:
        raw = extract_blocksec_payload(norm)
        payload = sanitize_blocksec_payload(raw)
        blocksec_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        result["blocksec_json"] = str(blocksec_path)
    except Exception as e:
        print(f"  [BlockSec] {norm}: {e}", file=sys.stderr)
        return result

    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="批量导出 BlockSec 与 EigenPhi JSON",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--csv",
        type=Path,
        help="CSV 文件路径（含 tx_hash 列）",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=Path("local/export_blocksec_eigenphi"),
        help="输出目录（默认: local/export_blocksec_eigenphi）",
    )
    parser.add_argument(
        "--eigenphi-only",
        action="store_true",
        help="仅导出 EigenPhi JSON（跳过 BlockSec）",
    )
    parser.add_argument(
        "--timeout-sec",
        type=int,
        default=60,
        help="单次请求超时秒数（默认 60）",
    )
    parser.add_argument(
        "--dotenv",
        default=str(ROOT / ".env"),
        help=".env 路径（用于 BLOCKSEC_COOKIE 等）",
    )
    parser.add_argument(
        "tx_hashes",
        nargs="*",
        help="交易哈希列表（当不使用 --csv 时）",
    )
    args = parser.parse_args()

    load_env_from_dotenv_if_missing(args.dotenv)

    if args.csv:
        if not args.csv.exists():
            print(f"错误: CSV 文件不存在: {args.csv}", file=sys.stderr)
            return 1
        tx_hashes = parse_csv_tx_hashes(args.csv)
    else:
        tx_hashes = [h.strip() for h in args.tx_hashes if h.strip()]

    if not tx_hashes:
        print("错误: 未提供 tx_hash。请使用 --csv 或传入 tx_hashes。", file=sys.stderr)
        return 1

    output_dir = args.output_dir
    if not output_dir.is_absolute():
        output_dir = (ROOT / output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"导出 {len(tx_hashes)} 笔交易到 {output_dir}")
    if args.eigenphi_only:
        print("（仅 EigenPhi，跳过 BlockSec）")

    success_eigenphi = 0
    success_blocksec = 0
    for i, tx_hash in enumerate(tx_hashes):
        print(f"[{i + 1}/{len(tx_hashes)}] {tx_hash[:18]}...")
        r = export_one(
            tx_hash,
            output_dir,
            eigenphi_only=args.eigenphi_only,
            timeout_sec=args.timeout_sec,
        )
        if r["eigenphi_json"]:
            success_eigenphi += 1
        if r["blocksec_json"]:
            success_blocksec += 1

    print(f"\n完成: EigenPhi {success_eigenphi}/{len(tx_hashes)}, BlockSec {success_blocksec}/{len(tx_hashes)}")
    return 0 if success_eigenphi > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
