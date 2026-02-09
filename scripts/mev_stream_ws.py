#!/usr/bin/env python3
"""
连接 EigenPhi MCP WebSocket，调用 get_eigenphi_mev_stream 并读取返回/推送数据。
用法:
  python mev_stream_ws.py -H "X-API-Key: eigenphi123" ws://127.0.0.1:8080/
  X_API_KEY=eigenphi123 python mev_stream_ws.py ws://127.0.0.1:8080/
依赖: pip install websockets
"""
import asyncio
import json
import os
import sys
import time

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


def _dump_content(result: dict) -> None:
    """打印 tools/call 返回的 content 内容。"""
    content = result.get("content") or []
    for item in content:
        kind = item.get("type", "text")
        if kind == "text" and item.get("text"):
            print(item["text"])
        else:
            print(json.dumps(item, ensure_ascii=False, indent=2))


async def main(url: str, extra_headers: dict, stream_seconds: float) -> None:
    kw = {"close_timeout": 2, "open_timeout": 10}
    if extra_headers:
        kw["additional_headers"] = extra_headers
    async with websockets.connect(url, **kw) as ws:
        # 1. initialize
        await ws.send(
            json.dumps({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"roots": {"listChanged": True}, "sampling": {}},
                    "clientInfo": {"name": "mev-stream-client", "version": "1.0.0"},
                },
            })
        )
        init_resp = json.loads(await ws.recv())
        if "error" in init_resp:
            print("initialize 失败:", json.dumps(init_resp, indent=2, ensure_ascii=False))
            return
        print("initialize OK, server:", init_resp.get("result", {}).get("serverInfo"), "\n")

        # 2. tools/call get_eigenphi_mev_stream
        call_req = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": "get_eigenphi_mev_stream", "arguments": {}},
        }
        await ws.send(json.dumps(call_req))

        # 3. 读首条响应
        try:
            msg = await asyncio.wait_for(ws.recv(), timeout=30.0)
        except asyncio.TimeoutError:
            print("(30s 内未收到 get_eigenphi_mev_stream 响应)")
            return
        call_resp = json.loads(msg)
        if "error" in call_resp:
            print("tools/call 失败:", json.dumps(call_resp, indent=2, ensure_ascii=False))
            return
        result = call_resp.get("result") or {}
        print("--- get_eigenphi_mev_stream 返回 ---")
        _dump_content(result)
        if result.get("isError"):
            print("(工具执行报错)")
            return

        # 4. 若需“流式”读取：在指定秒数内继续收消息并打印
        if stream_seconds > 0:
            print("\n--- 后续推送 (%.0fs 内) ---" % stream_seconds)
            deadline = time.monotonic() + stream_seconds
            while time.monotonic() < deadline:
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=2.0)
                except asyncio.TimeoutError:
                    continue
                try:
                    obj = json.loads(msg)
                    if "result" in obj and "content" in obj["result"]:
                        _dump_content(obj["result"])
                    else:
                        print(msg)
                except json.JSONDecodeError:
                    print(msg)


if __name__ == "__main__":
    headers, rest = _parse_headers(sys.argv[1:])
    url = rest[0] if rest else "ws://127.0.0.1:8080/"
    stream_seconds = 0.0
    if "--stream" in rest:
        idx = rest.index("--stream")
        if idx + 1 < len(rest):
            try:
                stream_seconds = float(rest[idx + 1])
            except ValueError:
                pass
        rest = [x for i, x in enumerate(rest) if i != idx and i != idx + 1]
        url = rest[0] if rest else url
    if headers:
        print("使用请求头:", ", ".join("%s: ***" % k for k in headers))
    asyncio.run(main(url, headers, stream_seconds))
