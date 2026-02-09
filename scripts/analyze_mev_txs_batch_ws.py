#!/usr/bin/env python3
"""
对给定的一批 MEV 交易哈希，通过 EigenPhi MCP WebSocket 批量拉取
get_eigenphi_tx_mev 与 get_eigenphi_tx_mev_analysis，并输出深入分析报告。

用法:
  python analyze_mev_txs_batch_ws.py -H "X-API-Key: eigenphi123" ws://127.0.0.1:8080/ --tx-hashes "0x... 0x..."
  python analyze_mev_txs_batch_ws.py --tx-file hashes.txt ws://127.0.0.1:8080/ -o report.md
"""
import argparse
import asyncio
import json
import os
import sys
from typing import Any, Dict, List, Optional, Tuple

try:
    import websockets
except ImportError:
    print("请先安装: pip install websockets", file=sys.stderr)
    sys.exit(1)


async def _call_tool(
    ws, req_id: int, name: str, arguments: dict, timeout: float = 120.0
) -> Optional[dict]:
    await ws.send(
        json.dumps(
            {
                "jsonrpc": "2.0",
                "id": req_id,
                "method": "tools/call",
                "params": {"name": name, "arguments": arguments},
            }
        )
    )
    try:
        msg = await asyncio.wait_for(ws.recv(), timeout=timeout)
    except asyncio.TimeoutError:
        return None
    try:
        resp = json.loads(msg)
    except json.JSONDecodeError:
        return None
    if resp.get("error"):
        return None
    return resp.get("result")


def _extract_text(result: Optional[dict]) -> str:
    if not result:
        return ""
    parts = []
    for item in (result.get("content") or []):
        if item.get("type") == "text" and item.get("text"):
            parts.append(item["text"])
    return "\n".join(parts)


async def main(
    url: str,
    extra_headers: dict,
    tx_hashes: List[str],
    out_md: Optional[str],
    analysis_timeout: float,
) -> None:
    kw = {"close_timeout": 2, "open_timeout": 10}
    if extra_headers:
        kw["additional_headers"] = extra_headers

    results: List[Tuple[str, Optional[dict], Optional[dict]]] = []

    async with websockets.connect(url, **kw) as ws:
        await ws.send(
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {"roots": {"listChanged": True}, "sampling": {}},
                        "clientInfo": {"name": "analyze-mev-batch", "version": "1.0.0"},
                    },
                }
            )
        )
        init_resp = json.loads(await ws.recv())
        if init_resp.get("error"):
            print("initialize 失败", file=sys.stderr)
            return

        for idx, tx_hash in enumerate(tx_hashes):
            tx_hash = tx_hash.strip()
            if not tx_hash or not tx_hash.startswith("0x"):
                continue
            print("拉取 [%d/%d] %s..." % (idx + 1, len(tx_hashes), tx_hash[:18] + "…"), flush=True)
            mev_result = await _call_tool(
                ws, 100 + idx * 2, "get_eigenphi_tx_mev",
                {"tx_hash": tx_hash, "include_raw": False},
                timeout=60.0,
            )
            analysis_result = await _call_tool(
                ws, 100 + idx * 2 + 1, "get_eigenphi_tx_mev_analysis",
                {"tx_hash": tx_hash, "max_steps": 10},
                timeout=analysis_timeout,
            )
            results.append((tx_hash, mev_result, analysis_result))

    # 写出报告
    lines = [
        "# MEV 高 ROI 交易深入分析报告",
        "",
        "本报告针对 profit/cost > 1 的 11 笔 EigenPhi MEV 交易，汇总摘要与策略分析。",
        "",
        "---",
        "",
    ]

    for idx, (tx_hash, mev_result, analysis_result) in enumerate(results):
        mev_text = _extract_text(mev_result)
        analysis_text = _extract_text(analysis_result)

        lines.append("## 交易 %d：`%s`" % (idx + 1, tx_hash))
        lines.append("")
        lines.append("- **EigenPhi PnL**: https://eigenphi.io/mev/ethereum/tx/%s" % tx_hash)
        lines.append("")
        lines.append("### MEV 摘要")
        lines.append("")
        if mev_text:
            lines.append("```")
            lines.append(mev_text.strip())
            lines.append("```")
        else:
            lines.append("*(拉取失败或为空)*")
        lines.append("")
        lines.append("### 策略分析")
        lines.append("")
        if analysis_text:
            lines.append(analysis_text.strip())
        else:
            lines.append("*(策略分析超时或未返回)*")
        lines.append("")
        lines.append("---")
        lines.append("")

    report = "\n".join(lines)
    print("\n" + "=" * 60)
    print(report[: 4000] + ("…" if len(report) > 4000 else ""))
    print("=" * 60)

    if out_md:
        with open(out_md, "w", encoding="utf-8") as f:
            f.write(report)
        print("已写入 %s" % out_md)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="批量拉取 MEV 交易摘要与策略分析并输出报告")
    parser.add_argument("url", nargs="?", default="ws://127.0.0.1:8080/", help="EigenPhi MCP WebSocket URL")
    parser.add_argument("--tx-hashes", type=str, default="", help="空格分隔的交易哈希")
    parser.add_argument("--tx-file", type=str, default="", help="每行一个交易哈希的文件")
    parser.add_argument("-o", "--out", type=str, default="", help="输出 Markdown 报告路径")
    parser.add_argument("--analysis-timeout", type=float, default=120.0, help="单笔策略分析超时(秒)")
    parser.add_argument("-H", "--header", action="append", dest="headers", default=[], metavar="K: V")
    args = parser.parse_args()

    hashes: List[str] = []
    if args.tx_file and os.path.isfile(args.tx_file):
        with open(args.tx_file, encoding="utf-8") as f:
            hashes = [ln.strip() for ln in f if ln.strip().startswith("0x")]
    if args.tx_hashes:
        hashes = [h.strip() for h in args.tx_hashes.split() if h.strip().startswith("0x")]
    if not hashes:
        print("请提供 --tx-hashes 或 --tx-file", file=sys.stderr)
        sys.exit(2)

    headers = {}
    if os.environ.get("X_API_KEY", "").strip():
        headers["X-API-Key"] = os.environ.get("X_API_KEY", "").strip()
    for h in args.headers:
        if ":" in h:
            k, v = h.split(":", 1)
            headers[k.strip()] = v.strip()

    asyncio.run(
        main(
            args.url,
            headers,
            hashes,
            args.out or None,
            args.analysis_timeout,
        )
    )
