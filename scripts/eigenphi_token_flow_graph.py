#!/usr/bin/env python3
"""
从 EigenPhi analyseTransaction API 数据生成 Token Flow 图 (SVG)。

用法:
  # 从 API 拉取并生成
  python scripts/eigenphi_token_flow_graph.py 0xbf1dee0efe5798ae4a92a93cff53c0896ebd2d986b26ce7c472c7835b478d8c1

  # 从本地 JSON 文件生成
  python scripts/eigenphi_token_flow_graph.py --json path/to/analyseTransaction.json

  # 指定输出路径
  python scripts/eigenphi_token_flow_graph.py -o output.svg 0xbf1dee...
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import requests
except ImportError:
    requests = None

# 代币 -> 边颜色 (与 EigenPhi 风格接近)
TOKEN_COLORS: Dict[str, str] = {
    "ETH": "#4a90d9",       # 蓝色
    "WETH": "#2d7d46",      # 绿色
    "USDC": "#2775ca",
    "USDT": "#26a17b",
    "DAI": "#f4b731",
    "Shiryo-Inu": "#d4a017",  # 金色
}
DEFAULT_EDGE_COLOR = "#666666"


def _short_addr(addr: str) -> str:
    if not addr or len(addr) < 10:
        return addr
    return f"{addr[:6]}...{addr[-4:]}"


def _format_amount(amount_str: str, decimals: int, symbol: str) -> str:
    """格式化金额显示，避免过长。"""
    try:
        v = float(amount_str)
    except (ValueError, TypeError):
        return f"{amount_str} {symbol}"
    if v >= 1e12:
        return f"{v/1e12:.2f}T {symbol}"
    if v >= 1e9:
        return f"{v/1e9:.2f}B {symbol}"
    if v >= 1e6:
        return f"{v/1e6:.2f}M {symbol}"
    if v >= 1e3:
        return f"{v/1e3:.2f}K {symbol}"
    if v >= 1:
        return f"{v:.4g} {symbol}"
    return f"{v:.4g} {symbol}"


def _get_address_label(addr: str, address_tags: List[Dict], address_type_names: Dict[str, str]) -> str:
    """从 addressTags 和 addressTypeNames 获取地址可读标签。优先使用 Address 名称。"""
    addr_lower = addr.lower() if addr else ""
    addr_name = None
    tx_field = None
    is_leaf = False
    for tag_obj in address_tags or []:
        if (tag_obj.get("address") or "").lower() != addr_lower:
            continue
        for t in tag_obj.get("tags") or []:
            cat = t.get("categoryName") or ""
            val = t.get("value") or ""
            if cat == "Address" and val:
                addr_name = val
            elif cat == "TransactionField" and val in ("from", "to"):
                tx_field = val
            elif (t.get("category") == 8 or cat == "Others") and val == "leaf":
                is_leaf = True
        break
    if addr_name:
        return addr_name
    if tx_field:
        return f"👤 {tx_field}"
    if is_leaf:
        return "leaf"
    return _short_addr(addr)


def _build_dot(
    transfers: List[Dict],
    address_tags: List[Dict],
    address_type_names: Dict[str, str],
    tx_from: Optional[str] = None,
    tx_to: Optional[str] = None,
) -> str:
    """从 transfers 和 addressTags 构建 Graphviz DOT 字符串。"""
    lines: List[str] = [
        'digraph G {',
        '  rankdir=LR;',
        '  node [shape=ellipse, style=filled, fillcolor=white];',
        '  edge [fontsize=10];',
    ]

    # 收集所有参与地址并生成节点
    addrs: set = set()
    for t in transfers:
        addrs.add((t.get("from") or "").lower())
        addrs.add((t.get("to") or "").lower())
    addrs.discard("")

    # 节点 ID 映射（Graphviz 节点 ID 不能以数字开头）
    node_ids: Dict[str, str] = {}
    for i, addr in enumerate(sorted(addrs)):
        node_ids[addr] = f"n{i}"

    for addr in addrs:
        nid = node_ids[addr]
        label = _get_address_label(addr, address_tags, address_type_names)
        # 转义 DOT 特殊字符
        label_esc = label.replace('"', '\\"').replace("\n", " ")
        lines.append(f'  {nid} [label="{label_esc}"];')

    # 边
    for t in transfers:
        f = (t.get("from") or "").lower()
        to_addr = (t.get("to") or "").lower()
        if not f or not to_addr:
            continue
        nf = node_ids.get(f)
        nt = node_ids.get(to_addr)
        if not nf or not nt:
            continue

        token = t.get("token") or {}
        symbol = token.get("symbol") or "?"
        decimals = token.get("decimals") or 18
        amount_str = t.get("amount") or "0"
        step = t.get("transferStep", -1)

        type_name = t.get("typeName") or ""
        if t.get("type") == 1:
            type_label = "mint"
        elif t.get("type") == 2:
            type_label = "burn"
        else:
            type_label = ""

        amount_str = _format_amount(amount_str, decimals, symbol)
        if type_label:
            label = f"{step} {type_label}: {amount_str}"
        else:
            label = f"{step} {amount_str}"

        color = TOKEN_COLORS.get(symbol, DEFAULT_EDGE_COLOR)
        label_esc = label.replace('"', '\\"')
        lines.append(f'  {nf} -> {nt} [label="{label_esc}", color="{color}", fontcolor="{color}"];')

    lines.append("}")
    return "\n".join(lines)


def _fetch_api(tx_hash: str) -> Optional[Dict]:
    """从 EigenPhi API 拉取 analyseTransaction 数据。"""
    if not requests:
        print("需要安装 requests: pip install requests", file=sys.stderr)
        return None
    url = f"https://eigenphi.io/api/v1/analyseTransaction?chain=ALL&enableCallStack=on&tx={tx_hash}"
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        data = r.json()
        if data.get("status") != "ok":
            return None
        result = data.get("result") or []
        if not result:
            return None
        return result[0]
    except Exception as e:
        print(f"API 请求失败: {e}", file=sys.stderr)
        return None


def _load_json(path: Path) -> Optional[Dict]:
    """从本地 JSON 文件加载。"""
    try:
        text = path.read_text(encoding="utf-8")
        data = json.loads(text)
        if data.get("status") == "ok":
            result = data.get("result") or []
            if result:
                return result[0]
        # 可能是直接 result[0] 结构
        if "transaction" in data and "transfers" in data.get("transaction", {}):
            return data
        return None
    except Exception as e:
        print(f"读取 JSON 失败: {e}", file=sys.stderr)
        return None


def _build_mermaid(
    transfers: List[Dict],
    address_tags: List[Dict],
    address_type_names: Dict[str, str],
) -> str:
    """构建 Mermaid flowchart，可在浏览器/IDE 中渲染。"""
    lines = ["flowchart LR"]
    addrs: set = set()
    for t in transfers:
        addrs.add((t.get("from") or "").lower())
        addrs.add((t.get("to") or "").lower())
    addrs.discard("")

    node_ids: Dict[str, str] = {}
    for i, addr in enumerate(sorted(addrs)):
        safe = f"n{i}"
        node_ids[addr] = safe

    for addr in addrs:
        nid = node_ids[addr]
        label = _get_address_label(addr, address_tags, address_type_names)
        label_esc = label.replace('"', "#quot;").replace("]", "&#93;")
        lines.append(f'    {nid}["{label_esc}"]')

    for t in transfers:
        f = (t.get("from") or "").lower()
        to_addr = (t.get("to") or "").lower()
        if not f or not to_addr:
            continue
        nf = node_ids.get(f)
        nt = node_ids.get(to_addr)
        if not nf or not nt:
            continue
        token = t.get("token") or {}
        symbol = token.get("symbol") or "?"
        decimals = token.get("decimals") or 18
        amount_str = t.get("amount") or "0"
        step = t.get("transferStep", -1)
        type_label = "mint: " if t.get("type") == 1 else "burn: " if t.get("type") == 2 else ""
        amount_str = _format_amount(amount_str, decimals, symbol)
        label = f"{step} {type_label}{amount_str}"
        label_esc = label.replace('"', "'")
        lines.append(f'    {nf} -->|"{label_esc}"| {nt}')

    return "\n".join(lines)


def _render_dot_to_svg(dot_str: str) -> Optional[str]:
    """使用 graphviz 将 DOT 转为 SVG。"""
    try:
        import graphviz
        try:
            # graphviz Python 包底层通常仍依赖系统 `dot` 可执行文件。
            # 因此这里即使 import 成功，也可能因为缺少 `dot` 而失败。
            g = graphviz.Source(dot_str)
            return g.pipe(format="svg").decode("utf-8")
        except Exception as e:
            # 回退到直接调用系统 `dot`，尽量给到更明确的错误信息。
            print(f"graphviz 渲染失败（将尝试 dot 命令回退）: {e}", file=sys.stderr)
    except ImportError:
        pass
    # 回退到系统 dot 命令
    import subprocess
    try:
        proc = subprocess.run(
            ["dot", "-Tsvg"],
            input=dot_str.encode("utf-8"),
            capture_output=True,
            timeout=10,
        )
        if proc.returncode == 0 and proc.stdout:
            return proc.stdout.decode("utf-8")
        if proc.stderr:
            err = proc.stderr.decode("utf-8", errors="replace").strip()
            if err:
                print(f"dot 渲染失败: {err}", file=sys.stderr)
    except FileNotFoundError:
        print(
            "未找到 `dot` 命令。请安装系统 Graphviz（如 macOS: brew install graphviz；Debian/Ubuntu: apt-get install graphviz），"
            "或安装并确保 `dot` 在 PATH 中。",
            file=sys.stderr,
        )
    except Exception as e:
        print(f"渲染失败: {e}", file=sys.stderr)
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="从 EigenPhi analyseTransaction 数据生成 Token Flow 图")
    parser.add_argument("tx_hash", nargs="?", help="交易哈希 (0x...)")
    parser.add_argument("--json", "-j", type=Path, help="本地 JSON 文件路径")
    parser.add_argument("-o", "--output", type=Path, help="输出 SVG 路径")
    parser.add_argument("--dot-only", action="store_true", help="仅输出 DOT，不渲染")
    parser.add_argument("--mermaid", "-m", action="store_true", help="输出 Mermaid 格式 (可在浏览器/IDE 中渲染)")
    parser.add_argument("--html", action="store_true", help="输出 HTML 文件 (含 Mermaid 渲染，可直接在浏览器打开)")
    args = parser.parse_args()

    data: Optional[Dict] = None
    if args.json:
        data = _load_json(args.json)
    elif args.tx_hash:
        if re.match(r"^0x[a-fA-F0-9]{64}$", args.tx_hash):
            data = _fetch_api(args.tx_hash)
        else:
            print("无效的交易哈希", file=sys.stderr)
            return 1
    else:
        parser.print_help()
        return 1

    if not data:
        print("无法获取数据", file=sys.stderr)
        return 1

    tx_obj = data.get("transaction") or data
    transfers = tx_obj.get("transfers") or []
    address_tags = tx_obj.get("addressTags") or []
    address_type_names = tx_obj.get("addressTypeNames") or {}
    tx_info = tx_obj.get("transaction") or tx_obj
    tx_from = tx_info.get("from")
    tx_to = tx_info.get("to")

    if not transfers:
        print("无 transfers 数据", file=sys.stderr)
        return 1

    dot_str = _build_dot(transfers, address_tags, address_type_names, tx_from, tx_to)
    mermaid_str = _build_mermaid(transfers, address_tags, address_type_names)

    if args.dot_only:
        print(dot_str)
        return 0

    if args.mermaid:
        out_path = args.output or Path("outputs/token_flow.mmd")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(mermaid_str, encoding="utf-8")
        print(f"已生成 Mermaid: {out_path.absolute()}")
        print("可在 https://mermaid.live 或 VS Code Mermaid 插件中预览")
        return 0

    if args.html:
        html_content = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Token Flow Graph</title>
  <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
</head>
<body>
  <div class="mermaid">
{mermaid_str}
  </div>
  <script>mermaid.initialize({{startOnLoad:true}});</script>
</body>
</html>"""
        out_path = args.output or Path("outputs/token_flow.html")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(html_content, encoding="utf-8")
        print(f"已生成 HTML: {out_path.absolute()}")
        print("在浏览器中打开即可查看")
        return 0

    svg = _render_dot_to_svg(dot_str)
    if not svg:
        return 1

    out_path = args.output
    if not out_path:
        tx = args.tx_hash or "out"
        out_path = Path(f"outputs/token_flow_{tx[:20]}.svg")
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(svg, encoding="utf-8")
    print(f"已生成: {out_path.absolute()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
