#!/usr/bin/env python3
"""按 tx hash 一键拉取数据并生成业务语义结构树。"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from calltrace.services.tx_hash_semantic_pipeline import (  # noqa: E402
    load_env_from_dotenv_if_missing,
    run_pipeline,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="tx hash -> 三源数据 -> OpenAI Shell 语义树")
    parser.add_argument("--tx-hash", required=True, help="目标交易哈希（0x + 64 hex）")
    parser.add_argument(
        "--rule-json",
        default="local/sample0x8c/phase_rule.json",
        help="phase rule JSON 路径",
    )
    parser.add_argument(
        "--output-root",
        default="local/tx_runs",
        help="输出根目录（最终会生成 output_root/{tx_hash}/...）",
    )
    parser.add_argument(
        "--model",
        default="gpt-5.2",
        help="OpenAI Responses 模型（需支持 shell 工具）",
    )
    parser.add_argument("--max-turns", type=int, default=20, help="shell 推理最大轮数")
    parser.add_argument("--timeout-sec", type=int, default=60, help="下载超时秒数")
    parser.add_argument(
        "--workdir",
        default=str(ROOT),
        help="本地 shell 命令执行目录",
    )
    parser.add_argument(
        "--dotenv",
        default=str(ROOT / ".env"),
        help="环境变量文件路径（仅在变量缺失时补充）",
    )
    args = parser.parse_args()

    load_env_from_dotenv_if_missing(args.dotenv)

    rule_json_path = Path(args.rule_json)
    if not rule_json_path.is_absolute():
        rule_json_path = (ROOT / rule_json_path).resolve()

    output_root = Path(args.output_root)
    if not output_root.is_absolute():
        output_root = (ROOT / output_root).resolve()

    workdir = Path(args.workdir)
    if not workdir.is_absolute():
        workdir = (ROOT / workdir).resolve()

    artifacts = run_pipeline(
        tx_hash=args.tx_hash,
        output_root=output_root,
        rule_json_path=rule_json_path,
        model=args.model,
        max_turns=args.max_turns,
        timeout_sec=args.timeout_sec,
        workdir=workdir,
    )

    print(str(artifacts.eigenphi_json))
    print(str(artifacts.eigenphi_svg))
    print(str(artifacts.blocksec_json))
    print(str(artifacts.selector_signatures_json))
    print(str(artifacts.semantic_markdown))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
