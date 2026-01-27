from __future__ import annotations

import base64
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def parse_block_mev_text(text: str) -> Dict[str, Any]:
    """解析区块 MEV (Maximal Extractable Value) 文本数据。"""
    lines = text.strip().split("\n")
    result: Dict[str, Any] = {
        "block_number": None,
        "type_summaries": [],
        "transactions": [],
    }

    current_tx: Optional[Dict[str, Any]] = None

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue

        if line.startswith("区块 ") and "MEV 汇总:" in line:
            match = re.search(r"区块 (\d+)", line)
            if match:
                result["block_number"] = int(match.group(1))
            continue

        if line.startswith("- 类型汇总:"):
            continue
        if line.startswith("  - "):
            match = re.match(
                r"  - (\w+): Profit ([\d.+-]+) USD, Cost ([\d.+-]+) USD, Revenue ([\d.+-]+) USD",
                line,
            )
            if match:
                result["type_summaries"].append(
                    {
                        "type": match.group(1),
                        "profit": match.group(2),
                        "cost": match.group(3),
                        "revenue": match.group(4),
                    }
                )
            continue

        if line.startswith("- 交易列表:"):
            continue
        if re.match(r"\s*- \[(\d+)\] (0x[a-fA-F0-9]+)", line):
            match = re.match(r"\s*- \[(\d+)\] (0x[a-fA-F0-9]+)", line)
            if match:
                if current_tx:
                    result["transactions"].append(current_tx)
                current_tx = {
                    "index": int(match.group(1)),
                    "tx_hash": match.group(2),
                    "types": [],
                    "sandwich_role": None,
                    "profit": None,
                    "cost": None,
                    "revenue": None,
                    "pnl_url": None,
                    "eigentx_url": None,
                }
            continue

        if current_tx is None:
            continue

        if "- Types: " in line:
            types_str = line.split("- Types: ")[1].strip()
            current_tx["types"] = [item.strip() for item in types_str.split(",") if item.strip()]
        elif "- Sandwich Role: " in line:
            current_tx["sandwich_role"] = line.split("- Sandwich Role: ")[1].strip()
        elif "- Profit: " in line:
            profit_str = line.split("- Profit: ")[1].strip()
            current_tx["profit"] = profit_str.replace(" USD", "").strip()
        elif "- Cost: " in line:
            cost_str = line.split("- Cost: ")[1].strip()
            current_tx["cost"] = cost_str.replace(" USD", "").strip()
        elif "- Revenue: " in line:
            revenue_str = line.split("- Revenue: ")[1].strip()
            current_tx["revenue"] = revenue_str.replace(" USD", "").strip()
        elif "- EigenPhi PnL: " in line:
            current_tx["pnl_url"] = line.split("- EigenPhi PnL: ")[1].strip()
        elif "- EigenTx: " in line:
            current_tx["eigentx_url"] = line.split("- EigenTx: ")[1].strip()

    if current_tx:
        result["transactions"].append(current_tx)

    return result


def _safe_float(value: Optional[str]) -> float:
    try:
        return float(value) if value is not None else 0.0
    except ValueError:
        return 0.0


def _build_svg_filename(tx_hash: str) -> str:
    return f"{tx_hash[:20]}_flow.svg"


def _build_mev_block_css(include_body: bool, embedded: bool) -> str:
    base_font = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif"
    min_height = "100vh" if not embedded else "auto"
    css = f"""
.mev-block-viewer {{
    font-family: {base_font};
    margin: 0;
    padding: 20px;
    background-color: #f5f5f5;
    min-height: {min_height};
}}
.mev-block-viewer .container {{
    max-width: 1400px;
    margin: 0 auto;
}}
.mev-block-viewer h1 {{
    color: #333;
    text-align: center;
    margin-bottom: 10px;
}}
.mev-block-viewer .subtitle {{
    text-align: center;
    color: #666;
    margin-bottom: 30px;
}}
.mev-block-viewer .transaction {{
    background: white;
    border-radius: 8px;
    padding: 20px;
    margin-bottom: 30px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}}
.mev-block-viewer .transaction-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 15px;
    padding-bottom: 10px;
    border-bottom: 2px solid #e0e0e0;
}}
.mev-block-viewer .tx-index {{
    font-size: 18px;
    font-weight: bold;
    color: #2196F3;
}}
.mev-block-viewer .tx-hash {{
    font-family: 'Courier New', monospace;
    font-size: 14px;
    color: #666;
}}
.mev-block-viewer .tx-type {{
    display: inline-block;
    padding: 4px 12px;
    border-radius: 12px;
    font-size: 12px;
    font-weight: bold;
}}
.mev-block-viewer .type-arbitrage {{
    background-color: #E3F2FD;
    color: #1976D2;
}}
.mev-block-viewer .type-liquidation {{
    background-color: #FFF3E0;
    color: #F57C00;
}}
.mev-block-viewer .type-sandwich {{
    background-color: #FCE4EC;
    color: #C2185B;
}}
.mev-block-viewer .tx-info {{
    display: flex;
    gap: 20px;
    margin-bottom: 15px;
    flex-wrap: wrap;
}}
.mev-block-viewer .info-item {{
    font-size: 14px;
}}
.mev-block-viewer .info-label {{
    color: #999;
    margin-right: 5px;
}}
.mev-block-viewer .info-value {{
    color: #333;
    font-weight: 500;
}}
.mev-block-viewer .profit-positive {{
    color: #4CAF50;
}}
.mev-block-viewer .profit-negative {{
    color: #F44336;
}}
.mev-block-viewer .tx-links {{
    display: flex;
    gap: 15px;
    margin-top: 10px;
    flex-wrap: wrap;
}}
.mev-block-viewer .tx-link {{
    display: inline-flex;
    align-items: center;
    padding: 6px 12px;
    background-color: #2196F3;
    color: white;
    text-decoration: none;
    border-radius: 4px;
    font-size: 13px;
    transition: background-color 0.2s;
}}
.mev-block-viewer .tx-link:hover {{
    background-color: #1976D2;
}}
.mev-block-viewer .tx-link.pnl {{
    background-color: #4CAF50;
}}
.mev-block-viewer .tx-link.pnl:hover {{
    background-color: #45a049;
}}
.mev-block-viewer .svg-container {{
    width: 100%;
    overflow-x: auto;
    border: 1px solid #e0e0e0;
    border-radius: 4px;
    padding: 10px;
    background: #fafafa;
    margin-top: 15px;
}}
.mev-block-viewer .svg-container svg {{
    display: block;
    margin: 0 auto;
}}
.mev-block-viewer .summary {{
    background: white;
    border-radius: 8px;
    padding: 20px;
    margin-bottom: 30px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}}
.mev-block-viewer .summary-stats {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 15px;
    margin-top: 15px;
}}
.mev-block-viewer .stat-item {{
    text-align: center;
}}
.mev-block-viewer .stat-value {{
    font-size: 24px;
    font-weight: bold;
    color: #2196F3;
}}
.mev-block-viewer .stat-label {{
    font-size: 12px;
    color: #999;
    margin-top: 5px;
}}
"""

    if include_body:
        css = f"body {{ margin: 0; }}\n{css}"

    return css.strip()


def build_mev_block_html(block_data: Dict[str, Any], embedded: bool) -> str:
    """生成 MEV 区块 Token Flow Graph HTML。"""
    block_number = block_data.get("block_number") or 0
    transactions: List[Dict[str, Any]] = block_data.get("transactions", [])

    total_profit = sum(_safe_float(tx.get("profit")) for tx in transactions)
    type_counts: Dict[str, int] = {}
    for tx in transactions:
        for tx_type in tx.get("types", []):
            type_counts[tx_type] = type_counts.get(tx_type, 0) + 1

    header_html = f"""
    <h1>区块 {block_number} - MEV 交易 Token Flow Graph</h1>
    <div class="subtitle">共 {len(transactions)} 笔 MEV 交易 | 总利润: {total_profit:+.2f} USD</div>
    <div class="summary">
        <h2>区块汇总</h2>
        <div class="summary-stats">
            <div class="stat-item">
                <div class="stat-value">{len(transactions)}</div>
                <div class="stat-label">MEV 交易数</div>
            </div>
            <div class="stat-item">
                <div class="stat-value profit-positive">{total_profit:+.2f}</div>
                <div class="stat-label">总利润 (USD)</div>
            </div>
    """
    for tx_type, count in type_counts.items():
        header_html += f"""
            <div class="stat-item">
                <div class="stat-value">{count}</div>
                <div class="stat-label">{tx_type} 交易</div>
            </div>
        """
    header_html += """
        </div>
    </div>
    """

    tx_html = ""
    for tx in transactions:
        tx_types = tx.get("types", [])
        tx_type_class = "type-arbitrage"
        if "Liquidation" in tx_types:
            tx_type_class = "type-liquidation"
        elif "Sandwich" in tx_types:
            tx_type_class = "type-sandwich"

        profit_value = tx.get("profit")
        profit_number = _safe_float(profit_value)
        profit_class = "profit-positive" if profit_value is not None and profit_number >= 0 else "profit-negative"
        profit_sign = "+" if profit_value is not None and profit_number >= 0 else ""
        profit_display = profit_value if profit_value is not None else "-"
        cost_display = tx.get("cost") or "-"
        revenue_display = tx.get("revenue") or "-"
        types_text = ", ".join(tx_types) if tx_types else "Unknown"

        svg_filename = _build_svg_filename(tx.get("tx_hash", ""))
        svg_path = f"/mev/block/{block_number}/{svg_filename}"

        tx_html += f"""
    <div class="transaction">
        <div class="transaction-header">
            <div>
                <span class="tx-index">[{tx.get("index", "-")}]</span>
                <span class="tx-hash">{tx.get("tx_hash", "")}</span>
            </div>
            <span class="tx-type {tx_type_class}">{types_text}</span>
        </div>
        <div class="tx-info">
            <div class="info-item">
                <span class="info-label">利润:</span>
                <span class="info-value {profit_class}">{profit_sign}{profit_display} USD</span>
            </div>
            <div class="info-item">
                <span class="info-label">成本:</span>
                <span class="info-value">{cost_display} USD</span>
            </div>
            <div class="info-item">
                <span class="info-label">收入:</span>
                <span class="info-value">{revenue_display} USD</span>
            </div>
    """
        sandwich_role = tx.get("sandwich_role")
        if sandwich_role:
            tx_html += f"""
            <div class="info-item">
                <span class="info-label">Sandwich Role:</span>
                <span class="info-value">{sandwich_role}</span>
            </div>
        """

        tx_html += """
        </div>
        <div class="tx-links">
    """
        pnl_url = tx.get("pnl_url")
        if pnl_url:
            tx_html += f"""
            <a href="{pnl_url}" target="_blank" class="tx-link pnl">📊 EigenPhi PnL</a>
        """
        eigentx_url = tx.get("eigentx_url")
        if eigentx_url:
            tx_html += f"""
            <a href="{eigentx_url}" target="_blank" class="tx-link">🔗 EigenTx</a>
        """

        tx_html += f"""
        </div>
        <div class="svg-container">
            <img src="{svg_path}" alt="Token Flow Graph" style="width: 100%; height: auto; max-width: 100%;" onerror="this.style.display='none'; this.nextElementSibling.style.display='block';">
            <div style="display: none; padding: 20px; text-align: center; color: #999;">
                <p>SVG 图加载失败</p>
                <a href="{svg_path}" target="_blank">直接打开 SVG 文件</a>
            </div>
        </div>
    </div>
    """

    content_html = f"""
<div class="mev-block-viewer">
  <div class="container">
    {header_html}
    {tx_html}
  </div>
</div>
"""

    css = _build_mev_block_css(include_body=not embedded, embedded=embedded)
    if embedded:
        return f"<style>{css}</style>\n{content_html}"

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>区块 {block_number} - MEV 交易 Token Flow Graph</title>
  <style>
  {css}
  </style>
</head>
<body>
  {content_html}
</body>
</html>
"""


class MevBlockService:
    """MEV (Maximal Extractable Value) 区块数据拉取与 HTML 生成服务。"""

    def __init__(self, mcp_server: str, timeout_seconds: int, base_dir: Optional[Path] = None) -> None:
        self._mcp_server = mcp_server.strip()
        self._timeout_seconds = timeout_seconds
        self._base_dir = base_dir or Path(__file__).resolve().parents[3]
        self._token_flow_dir = self._base_dir / "token_flow_graphs"

    def get_or_build_block(self, block_number: int, refresh: bool = False) -> Tuple[Optional[str], Optional[str]]:
        """获取或生成区块 HTML，返回 (html_fragment, error)。"""
        block_dir = self._token_flow_dir / f"block_{block_number}"
        block_dir.mkdir(parents=True, exist_ok=True)
        index_file = block_dir / "index.html"

        if index_file.exists() and not refresh:
            meta = self._load_block_metadata(block_dir)
            if meta and meta.get("transactions"):
                embedded = build_mev_block_html(meta, embedded=True)
                return embedded, None

        if not self._mcp_server:
            return None, "MCP_SERVER 未配置，请设置 MCP_EIGENPHI_SERVER"

        block_data = self._get_block_mev_data(block_number)
        if not block_data:
            return None, f"区块 {block_number} 的 MEV 数据为空"

        block_number_resolved = block_data.get("block_number") or block_number
        block_data["block_number"] = block_number_resolved

        self._ensure_token_flow_svgs(block_number_resolved, block_data.get("transactions", []), block_dir)
        full_html = build_mev_block_html(block_data, embedded=False)
        index_file.write_text(full_html, encoding="utf-8")

        embedded_html = build_mev_block_html(block_data, embedded=True)
        meta_file = block_dir / "block_meta.json"
        meta_file.write_text(json.dumps(block_data, ensure_ascii=False, indent=2), encoding="utf-8")
        return embedded_html, None

    def _get_block_mev_data(self, block_number: int) -> Optional[Dict[str, Any]]:
        result = self._call_mcp_tool("get_eigenphi_block_mev", {"block_number": block_number})
        if result is None:
            return None
        text = self._extract_text(result)
        if not text:
            return None
        return parse_block_mev_text(text)

    def _ensure_token_flow_svgs(self, block_number: int, transactions: List[Dict[str, Any]], block_dir: Path) -> None:
        for tx in transactions:
            tx_hash = tx.get("tx_hash") or ""
            if not tx_hash:
                continue
            svg_filename = _build_svg_filename(tx_hash)
            svg_path = block_dir / svg_filename
            if svg_path.exists():
                continue
            svg_payload = self._call_mcp_tool("get_token_flow_graph", {"tx_hash": tx_hash})
            if svg_payload is None:
                continue
            svg_text, svg_bytes = self._extract_svg(svg_payload)
            if svg_bytes:
                svg_path.write_bytes(svg_bytes)
            elif svg_text:
                svg_path.write_text(svg_text, encoding="utf-8")

    def _call_mcp_tool(self, name: str, arguments: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """调用 MCP (Model Context Protocol) 工具并返回结果。"""
        request_payload = {"method": "tools/call", "params": {"name": name, "arguments": arguments}}
        env = os.environ.copy()
        try:
            result = subprocess.run(
                [self._mcp_server],
                input=json.dumps(request_payload),
                capture_output=True,
                text=True,
                timeout=self._timeout_seconds,
                env=env,
            )
        except subprocess.TimeoutExpired:
            return None
        except Exception:
            return None

        if result.returncode != 0:
            return None

        try:
            response = json.loads(result.stdout)
        except json.JSONDecodeError:
            return None

        if "error" in response:
            return None

        return response.get("result")

    def _extract_text(self, result: Dict[str, Any]) -> Optional[str]:
        content = result.get("content") or []
        for item in content:
            text = item.get("text")
            if text:
                return text
        return None

    def _extract_svg(self, result: Dict[str, Any]) -> Tuple[Optional[str], Optional[bytes]]:
        content = result.get("content") or []
        for item in content:
            if item.get("text"):
                text = item.get("text")
                if text:
                    return text, None
            data = item.get("data") or item.get("blob")
            if isinstance(data, str):
                try:
                    return None, base64.b64decode(data)
                except Exception:
                    continue
        return None, None

    def _load_block_metadata(self, block_dir: Path) -> Optional[Dict[str, Any]]:
        meta_file = block_dir / "block_meta.json"
        if meta_file.exists():
            try:
                return json.loads(meta_file.read_text(encoding="utf-8"))
            except Exception:
                return None
        return None
