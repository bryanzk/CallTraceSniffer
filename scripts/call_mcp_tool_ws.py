#!/usr/bin/env python3
"""通过 WebSocket 调用任意 MCP 工具并打印结果。用于 get_eigenphi_tx_mev 等。"""
import asyncio
import json
import os
import sys

try:
    import websockets
except ImportError:
    print("pip install websockets", file=sys.stderr)
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


async def main(url: str, extra_headers: dict, tool: str, arguments: dict) -> None:
    kw = {"close_timeout": 2, "open_timeout": 10}
    if extra_headers:
        kw["additional_headers"] = extra_headers
    async with websockets.connect(url, **kw) as ws:
        await ws.send(json.dumps({
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"roots": {"listChanged": True}, "sampling": {}},
                "clientInfo": {"name": "call-mcp-ws", "version": "1.0.0"},
            },
        }))
        init_resp = json.loads(await ws.recv())
        if "error" in init_resp:
            print(json.dumps(init_resp, indent=2, ensure_ascii=False))
            return
        call_req = {
            "jsonrpc": "2.0", "id": 2, "method": "tools/call",
            "params": {"name": tool, "arguments": arguments},
        }
        await ws.send(json.dumps(call_req))
        msg = await asyncio.wait_for(ws.recv(), timeout=60.0)
        call_resp = json.loads(msg)
        if "error" in call_resp:
            print(json.dumps(call_resp, indent=2, ensure_ascii=False))
            return
        result = call_resp.get("result") or {}
        for item in (result.get("content") or []):
            if item.get("type") == "text" and item.get("text"):
                print(item["text"])
            else:
                print(json.dumps(item, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    headers, rest = _parse_headers(sys.argv[1:])
    if len(rest) < 3:
        print("用法: call_mcp_tool_ws.py -H 'X-API-Key: x' <ws_url> <tool_name> '<json_arguments>'", file=sys.stderr)
        sys.exit(2)
    url, tool, arg_str = rest[0], rest[1], rest[2]
    try:
        arguments = json.loads(arg_str)
    except json.JSONDecodeError:
        arguments = {}
    asyncio.run(main(url, headers, tool, arguments))
