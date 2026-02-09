#!/usr/bin/env python3
"""
通过 WebSocket 连接 MCP 服务器，请求 tools/list 并打印工具列表。
支持认证头，用法与 websocat 类似：
  websocat -H 'X-API-Key: eigenphi123' wss://your-domain.com/mcp

用法（与 websocat -H 等效）:
  python list_mcp_tools_ws.py -H "X-API-Key: eigenphi123" wss://your-domain.com/mcp
  X_API_KEY=eigenphi123 python list_mcp_tools_ws.py wss://your-domain.com/mcp
依赖: pip install websockets
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
    """
    从环境变量 X_API_KEY 或命令行 -H 'X-API-Key: value' 构造请求头。
    与 websocat -H 'X-API-Key: eigenphi123' 等效。
    返回 (headers, 剩余 argv，其中第一个可为 URL)。
    """
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


async def main(url: str, extra_headers: dict) -> None:
    kw = {"close_timeout": 2, "open_timeout": 10}
    if extra_headers:
        kw["additional_headers"] = extra_headers
    async with websockets.connect(url, **kw) as ws:
        # 1. initialize
        init_req = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"roots": {"listChanged": True}, "sampling": {}},
                "clientInfo": {"name": "list-mcp-tools", "version": "1.0.0"},
            },
        }
        await ws.send(json.dumps(init_req))
        init_resp = json.loads(await ws.recv())
        if "error" in init_resp:
            print("initialize 失败:", json.dumps(init_resp, indent=2, ensure_ascii=False))
            return
        print("initialize OK, server:", init_resp.get("result", {}).get("serverInfo"))

        # 2. notifications/initialized（部分 MCP 如 eigenphi-blockchain 不支持，跳过）
        # await ws.send(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}))

        # 3. tools/list
        list_req = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {},
        }
        await ws.send(json.dumps(list_req))
        list_resp = json.loads(await ws.recv())
        if "error" in list_resp:
            print("tools/list 失败:", json.dumps(list_resp, indent=2, ensure_ascii=False))
            return

        tools = list_resp.get("result", {}).get("tools", [])
        print("\n--- %s 提供的 MCP 工具 (%d 个) ---\n" % (url, len(tools)))
        for i, t in enumerate(tools, 1):
            name = t.get("name", "")
            desc = t.get("description", "")
            schema = t.get("inputSchema", {})
            props = schema.get("properties", {})
            req = schema.get("required", [])
            params = ", ".join(
                "%s%s" % (k, " (必填)" if k in req else " (可选)")
                for k in list(props.keys()) or ["无"]
            )
            print("%d. %s" % (i, name))
            print("   描述: %s" % (desc or "-"))
            print("   参数: %s" % params)
            print()


if __name__ == "__main__":
    headers, rest = _parse_headers(sys.argv[1:])
    url = rest[0] if rest else "ws://127.0.0.1:8080"
    if headers:
        print("使用请求头:", ", ".join("%s: ***" % k for k in headers))
    asyncio.run(main(url, headers))
