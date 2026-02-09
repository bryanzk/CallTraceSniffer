#!/usr/bin/env python3
"""
通过 EigenPhi MCP WebSocket 调用 get_eigenphi_tx_mev_analysis，生成指定交易的 MEV 策略分析。
用法:
  python mev_analysis_ws.py -H "X-API-Key: eigenphi123" ws://127.0.0.1:8080/ 0x082872cd...
  python mev_analysis_ws.py -H "X-API-Key: eigenphi123" ws://127.0.0.1:8080/ 0x082872cd... --max-steps 10
"""
import asyncio
import json
import os
import sys

try:
    import websockets
except ImportError:
    print("请先安装: pip install websockets", file=sys.stderr)
    sys.exit(1)


def _parse_headers(args: list) -> tuple[dict, list]:
    headers = {}
    key = os.environ.get("X_API_KEY", "").strip()
    if key:
        headers["X-API-Key"] = key
    rest = []
    i = 0
    while i < len(args):
        a = args[i]
        if a in ("-H", "--header") and i + 1 < len(args):
            part = args[i + 1]
            if ":" in part:
                k, v = part.split(":", 1)
                headers[k.strip()] = v.strip()
            i += 2
            continue
        rest.append(a)
        i += 1
    return headers, rest


async def main(url: str, extra_headers: dict, tx_hash: str, max_steps) -> None:
    kw = {"close_timeout": 2, "open_timeout": 10}
    if extra_headers:
        kw["additional_headers"] = extra_headers
    async with websockets.connect(url, **kw) as ws:
        await ws.send(
            json.dumps({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"roots": {"listChanged": True}, "sampling": {}},
                    "clientInfo": {"name": "mev-analysis-client", "version": "1.0.0"},
                },
            })
        )
        init_resp = json.loads(await ws.recv())
        if "error" in init_resp:
            print("initialize 失败:", json.dumps(init_resp, indent=2, ensure_ascii=False))
            return
        print("initialize OK\n")

        arguments = {"tx_hash": tx_hash}
        if max_steps is not None:
            arguments["max_steps"] = max_steps
        call_req = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": "get_eigenphi_tx_mev_analysis", "arguments": arguments},
        }
        await ws.send(json.dumps(call_req))

        try:
            msg = await asyncio.wait_for(ws.recv(), timeout=60.0)
        except asyncio.TimeoutError:
            print("(60s 内未收到 get_eigenphi_tx_mev_analysis 响应)")
            return
        call_resp = json.loads(msg)
        if "error" in call_resp:
            print("tools/call 失败:", json.dumps(call_resp, indent=2, ensure_ascii=False))
            return
        result = call_resp.get("result") or {}
        content = result.get("content") or []
        for item in content:
            if item.get("type") == "text" and item.get("text"):
                print(item["text"])
            elif item:
                print(json.dumps(item, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    headers, rest = _parse_headers(sys.argv[1:])
    url = "ws://127.0.0.1:8080/"
    tx_hash = ""
    max_steps = None
    i = 0
    while i < len(rest):
        x = rest[i]
        if x == "--max-steps" and i + 1 < len(rest):
            try:
                max_steps = int(rest[i + 1])
            except ValueError:
                pass
            i += 2
            continue
        if x.startswith("0x") and len(x) == 66:
            tx_hash = x
            i += 1
            continue
        if "://" in x:
            url = x
        i += 1
    if not tx_hash:
        print("用法: mev_analysis_ws.py -H 'X-API-Key: ...' ws://127.0.0.1:8080/ <tx_hash> [--max-steps N]", file=sys.stderr)
        sys.exit(2)
    if headers:
        print("使用请求头:", ", ".join("%s: ***" % k for k in headers))
    asyncio.run(main(url, headers, tx_hash, max_steps))
