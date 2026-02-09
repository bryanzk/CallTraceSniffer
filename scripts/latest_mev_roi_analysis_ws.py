#!/usr/bin/env python3
"""
通过 EigenPhi MCP WebSocket 拉取最新 N 笔 MEV 交易，筛选 profit/cost > 1 的套利交易，
并对每笔调用 get_eigenphi_tx_mev_analysis 做策略分析。

用法:
  python latest_mev_roi_analysis_ws.py -H "X-API-Key: eigenphi123" ws://127.0.0.1:8080/
  python latest_mev_roi_analysis_ws.py --tx-count 50 --min-roi 1.0 ws://127.0.0.1:8080/
  X_API_KEY=eigenphi123 python latest_mev_roi_analysis_ws.py ws://127.0.0.1:8080/

依赖: pip install websockets
"""
import argparse
import asyncio
import json
import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

try:
    import websockets
except ImportError:
    print("请先安装: pip install websockets", file=sys.stderr)
    sys.exit(1)


def _parse_latest_mev_content(result: dict) -> List[Dict[str, Any]]:
    """
    从 get_eigenphi_latest_mev 的 tools/call 返回中解析出交易列表。
    支持 content[].text 为 JSON 字符串或 content 为结构化数据。
    每个元素需含 tx_hash/txHash，以及 profit、cost（或 summary.profit / summary.cost）。
    """
    txs: List[Dict[str, Any]] = []
    content = result.get("content") or []
    raw_text = ""
    for item in content:
        if item.get("type") == "text" and item.get("text"):
            raw_text += item["text"]
        elif isinstance(item, dict) and "text" in item:
            raw_text += item.get("text", "")

    if not raw_text.strip():
        return txs

    # 尝试整体解析为 JSON
    try:
        data = json.loads(raw_text)
        if isinstance(data, list):
            txs = data
        elif isinstance(data, dict):
            # 常见形态: { "txs": [...] } 或 { "data": [...] } 或 { "transactions": [...] }
            txs = (
                data.get("txs")
                or data.get("data")
                or data.get("transactions")
                or data.get("list")
                or []
            )
            if not isinstance(txs, list):
                txs = [data]
        else:
            txs = []
    except json.JSONDecodeError:
        # 若为逐行或半结构化文本，尝试提取 0x... 与数字
        txs = _parse_latest_mev_fallback(raw_text)

    return txs


# EigenPhi 返回的「  - #1 0x... | Type: ... | Profit: X | Cost: Y | ...」行格式
_RE_TXHASH = re.compile(r"0x[a-fA-F0-9]{64}")
_RE_PROFIT = re.compile(r"Profit:\s*([\d.]+)")
_RE_COST = re.compile(r"Cost:\s*([\d.]+)")


def _parse_latest_mev_fallback(text: str) -> List[Dict[str, Any]]:
    """从非 JSON 文本中尽量提取 tx_hash、profit、cost。优先匹配 EigenPhi 的「Profit: X | Cost: Y」行格式。"""
    txs = []
    lines = text.split("\n")
    for line in lines:
        h = _RE_TXHASH.search(line)
        p = _RE_PROFIT.search(line)
        c = _RE_COST.search(line)
        if h and p and c:
            tx_hash = h.group(0)
            profit = float(p.group(1))
            cost = float(c.group(1))
            txs.append(
                {
                    "tx_hash": tx_hash,
                    "txHash": tx_hash,
                    "profit": profit,
                    "cost": cost,
                }
            )
            continue
        # 通用回退：行内含 0x + 至少两个小数
        hash_re = re.compile(r"0x[a-fA-F0-9]{64}")
        numbers = re.compile(r"-?\d+\.?\d*")
        hashes = hash_re.findall(line)
        nums = [float(x) if "." in str(x) else int(x) for x in numbers.findall(line)]
        if hashes and len(nums) >= 2:
            txs.append(
                {
                    "tx_hash": hashes[0],
                    "txHash": hashes[0],
                    "profit": float(nums[0]),
                    "cost": float(nums[1]),
                }
            )
        elif hashes:
            txs.append({"tx_hash": hashes[0], "txHash": hashes[0], "profit": 0.0, "cost": 0.0})
    return txs


def _norm_tx(t: Dict[str, Any]) -> Tuple[Optional[str], float, float]:
    """从单条交易中提取 tx_hash, profit, cost。"""
    tx_hash = t.get("tx_hash") or t.get("txHash") or t.get("tx_hash_hex")
    if isinstance(tx_hash, str) and tx_hash.startswith("0x"):
        pass
    else:
        tx_hash = None

    def _get_num(*keys_and_paths: str) -> float:
        for k in keys_and_paths:
            if k in t and t[k] is not None:
                try:
                    return float(t[k])
                except (TypeError, ValueError):
                    pass
            # summary.profit 形式
            if "." in k:
                part, key = k.split(".", 1)
                if part in t and isinstance(t[part], dict):
                    v = t[part].get(key)
                    if v is not None:
                        try:
                            return float(v)
                        except (TypeError, ValueError):
                            pass
        return 0.0

    profit = _get_num("profit", "summary.profit", "Profit")
    cost = _get_num("cost", "summary.cost", "Cost")
    if "summary" in t and isinstance(t["summary"], dict):
        profit = float(t["summary"].get("profit", profit))
        cost = float(t["summary"].get("cost", cost))
    return tx_hash, profit, cost


def _extract_analysis_text(result: dict) -> str:
    """从 get_eigenphi_tx_mev_analysis 的返回中取出文本。"""
    parts = []
    for item in (result.get("content") or []):
        if item.get("type") == "text" and item.get("text"):
            parts.append(item["text"])
    return "\n".join(parts)


async def _call_tool(
    ws,
    req_id: int,
    name: str,
    arguments: dict,
    timeout: float = 90.0,
) -> Optional[dict]:
    """在已连接的 ws 上发 tools/call 并返回 result。"""
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


async def main(
    url: str,
    extra_headers: dict,
    tx_count: int,
    min_roi: float,
    max_analysis: Optional[int],
    out_json: Optional[str],
) -> None:
    kw = {"close_timeout": 2, "open_timeout": 10}
    if extra_headers:
        kw["additional_headers"] = extra_headers

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
                        "clientInfo": {"name": "latest-mev-roi-analysis", "version": "1.0.0"},
                    },
                }
            )
        )
        init_resp = json.loads(await ws.recv())
        if init_resp.get("error"):
            print("initialize 失败:", json.dumps(init_resp, indent=2, ensure_ascii=False), file=sys.stderr)
            return

        # 1) 拉取最新 tx_count 笔
        result = await _call_tool(
            ws, 2, "get_eigenphi_latest_mev", {"chain": "ethereum", "tx_count": tx_count}
        )
        if not result:
            print("get_eigenphi_latest_mev 调用超时或失败", file=sys.stderr)
            return

        txs = _parse_latest_mev_content(result)
        # 标准化并筛选 profit/cost > min_roi 且 cost > 0
        filtered: List[Tuple[str, float, float, Dict[str, Any]]] = []
        for t in txs:
            tx_hash, profit, cost = _norm_tx(t)
            if not tx_hash:
                continue
            if cost <= 0:
                continue
            roi = profit / cost
            if roi > min_roi:
                filtered.append((tx_hash, profit, cost, t))

        # 按 ROI 降序
        filtered.sort(key=lambda x: x[1] / x[2], reverse=True)

        print("=== 最新 %d 笔 MEV 中 profit/cost > %.2f 的交易共 %d 笔 ===\n" % (tx_count, min_roi, len(filtered)))
        if out_json:
            out_data = {"tx_count_requested": tx_count, "min_roi": min_roi, "filtered_count": len(filtered)}

        for idx, (tx_hash, profit, cost, raw) in enumerate(filtered):
            roi = profit / cost
            print("[%d] %s  profit=%.4f  cost=%.4f  ROI=%.2f" % (idx + 1, tx_hash, profit, cost, roi))
            if max_analysis is not None and idx >= max_analysis:
                print("(已达 --max-analysis %d，不再请求策略分析)\n" % max_analysis)
                if out_json:
                    out_data.setdefault("transactions", []).append(
                        {"tx_hash": tx_hash, "profit": profit, "cost": cost, "roi": roi, "analysis": None}
                    )
                continue

            analysis_result = await _call_tool(
                ws, 100 + idx, "get_eigenphi_tx_mev_analysis", {"tx_hash": tx_hash, "max_steps": 10}, timeout=180.0
            )
            if analysis_result:
                text = _extract_analysis_text(analysis_result)
                print("--- 策略分析 ---")
                print(text)
                print()
                if out_json:
                    out_data.setdefault("transactions", []).append(
                        {"tx_hash": tx_hash, "profit": profit, "cost": cost, "roi": roi, "analysis": text}
                    )
            else:
                print("(get_eigenphi_tx_mev_analysis 超时或失败)\n")
                if out_json:
                    out_data.setdefault("transactions", []).append(
                        {"tx_hash": tx_hash, "profit": profit, "cost": cost, "roi": roi, "analysis": None}
                    )

        if out_json:
            with open(out_json, "w", encoding="utf-8") as f:
                json.dump(out_data, f, ensure_ascii=False, indent=2)
            print("已写入 %s" % out_json)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="拉取最新 MEV，筛选 profit/cost>1 并做策略分析")
    parser.add_argument("url", nargs="?", default="ws://127.0.0.1:8080/", help="EigenPhi MCP WebSocket URL")
    parser.add_argument("--tx-count", "-n", type=int, default=50, help="最新 MEV 笔数（默认 50）")
    parser.add_argument("--min-roi", type=float, default=1.0, help="最小 ROI = profit/cost（默认 1.0）")
    parser.add_argument("--max-analysis", type=int, default=None, help="最多对前 N 笔做策略分析（默认全部）")
    parser.add_argument("--out-json", "-o", type=str, default=None, help="将结果写出为 JSON 文件")
    parser.add_argument("-H", "--header", action="append", dest="headers", default=[], metavar="Header: Value")
    args = parser.parse_args()

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
            tx_count=args.tx_count,
            min_roi=args.min_roi,
            max_analysis=args.max_analysis,
            out_json=args.out_json,
        )
    )
