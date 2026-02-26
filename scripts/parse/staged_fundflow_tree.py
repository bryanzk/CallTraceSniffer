#!/usr/bin/env python3
"""给定 txhash 生成分阶段资金树（JSON + Markdown）。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from calltrace.services.staged_fundflow_tree import (  # noqa: E402
    build_dynamic_semantic_tree,
    build_flow_tree,
    build_staged_fundflow_tree,
    load_tx_payload,
    render_dynamic_semantic_markdown,
    render_staged_tree_markdown,
)
from calltrace.services.semantic_report import (  # noqa: E402
    build_analyst_report,
    optional_llm_polish,
    render_analyst_markdown,
)


def _extract_transaction(payload: dict) -> dict:
    result = payload.get("result")
    if not isinstance(result, list) or not result:
        raise ValueError("输入缺少 result 或 result 为空")
    first = result[0]
    tx = first.get("transaction")
    if not isinstance(tx, dict):
        raise ValueError("result[0].transaction 缺失或非 object")
    if "transfers" not in tx and isinstance(first.get("transfers"), list):
        tx = dict(tx)
        tx["transfers"] = first.get("transfers")
    return tx


def main() -> int:
    parser = argparse.ArgumentParser(description="生成分阶段资金树")
    parser.add_argument("--tx-hash", required=True, help="交易哈希")
    parser.add_argument("--input-json", default="", help="本地 analyseTransaction JSON 文件")
    parser.add_argument("--fetch", action="store_true", help="缺少本地文件时联网拉取")
    parser.add_argument("--output-json", default="", help="输出 JSON 文件路径")
    parser.add_argument("--output-md", default="", help="输出 Markdown 文件路径")
    parser.add_argument("--dynamic-semantic", action="store_true", help="启用动态语义执行结构树输出")
    parser.add_argument("--semantic-output-json", default="", help="动态语义 JSON 输出路径")
    parser.add_argument("--semantic-output-md", default="", help="动态语义 Markdown 输出路径")
    parser.add_argument("--report", action="store_true", help="输出分析师报告（基于动态语义树）")
    parser.add_argument("--report-output-md", default="", help="分析师报告 Markdown 输出路径")
    parser.add_argument("--report-style", default="default", help="分析师报告风格")
    parser.add_argument("--report-llm", action="store_true", help="启用可选 LLM 润色（默认关闭）")
    parser.add_argument("--report-llm-provider", default="", help="LLM provider 占位参数（如 mock）")
    parser.add_argument("--strict", action="store_true", default=True, help="保守模式（默认）")
    parser.add_argument("--aggressive", action="store_false", dest="strict", help="激进模式")
    parser.add_argument("--include-static", action="store_true", help="保留 STATICCALL 节点")
    parser.add_argument("--prune", action="store_true", default=True, help="剪枝无转账节点（默认开启）")
    parser.add_argument("--no-prune", action="store_false", dest="prune", help="关闭剪枝")
    args = parser.parse_args()

    tx_hash = args.tx_hash.lower()
    input_json = Path(args.input_json) if args.input_json else None

    payload = load_tx_payload(tx_hash, input_json, args.fetch, ROOT / "outputs")
    tx = _extract_transaction(payload)

    result0 = payload["result"][0] if isinstance(payload.get("result"), list) and payload["result"] else {}
    flow_tree = build_flow_tree(tx, include_static=args.include_static, prune=args.prune)
    staged = build_staged_fundflow_tree(
        flow_tree,
        tx.get("transfers", []),
        address_meta={
            "addressGroups": result0.get("addressGroups") or [],
            "addressTags": result0.get("addressTags") or [],
        },
        tx_meta={
            "tx_hash": tx.get("transactionHash") or tx_hash,
            "from": tx.get("from"),
            "to": tx.get("to"),
            "miner": tx.get("miner"),
        },
    )
    markdown = render_staged_tree_markdown(staged, style="example")

    out_json = Path(args.output_json) if args.output_json else ROOT / "outputs" / f"{tx_hash}_staged_fundflow_tree.json"
    out_md = Path(args.output_md) if args.output_md else ROOT / "outputs" / f"{tx_hash}_staged_fundflow_tree.md"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.parent.mkdir(parents=True, exist_ok=True)

    out_json.write_text(json.dumps(staged, ensure_ascii=False, indent=2), encoding="utf-8")
    out_md.write_text(markdown, encoding="utf-8")

    print(str(out_json))
    print(str(out_md))

    if args.dynamic_semantic:
        semantic = build_dynamic_semantic_tree(payload, tx_hash, strict=args.strict)
        semantic_md = render_dynamic_semantic_markdown(semantic)
        semantic_json_path = (
            Path(args.semantic_output_json)
            if args.semantic_output_json
            else ROOT / "outputs" / f"{tx_hash}_dynamic_semantic_tree.json"
        )
        semantic_md_path = (
            Path(args.semantic_output_md)
            if args.semantic_output_md
            else ROOT / "outputs" / f"{tx_hash}_dynamic_semantic_tree.md"
        )
        semantic_json_path.parent.mkdir(parents=True, exist_ok=True)
        semantic_md_path.parent.mkdir(parents=True, exist_ok=True)
        semantic_json_path.write_text(json.dumps(semantic, ensure_ascii=False, indent=2), encoding="utf-8")
        semantic_md_path.write_text(semantic_md, encoding="utf-8")
        print(str(semantic_json_path))
        print(str(semantic_md_path))

        if args.report:
            _provider = args.report_llm_provider  # 占位，当前版本不启用外部调用
            report = build_analyst_report(semantic, style=args.report_style)
            report_md = render_analyst_markdown(report)
            report_md = optional_llm_polish(report_md, facts=semantic, enabled=args.report_llm)

            report_md_path = (
                Path(args.report_output_md)
                if args.report_output_md
                else ROOT / "outputs" / f"{tx_hash}_analyst_report.md"
            )
            report_md_path.parent.mkdir(parents=True, exist_ok=True)
            report_md_path.write_text(report_md, encoding="utf-8")
            print(str(report_md_path))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
