"""
Build Mermaid DAG output from IR V1 JSON.
"""
from __future__ import annotations

import html
from typing import Any, Dict, List, Tuple


SWAP_FIELDS = [
    "type",
    "protocolId",
    "poolId",
    "tokenIn",
    "tokenOut",
    "amountInBig",
    "amountOutBig",
    "isAmountIn",
    "zeroForOne",
    "recipient",
    "recipientType",
]

TRANSFER_FIELDS = [
    "type",
    "tokenId",
    "to",
    "amount",
]


def _fmt_value(value: Any) -> str:
    if value is None:
        return "null"
    return str(value)


def _escape(value: str) -> str:
    return html.escape(value, quote=False)


def _swap_row_data(node: Dict[str, Any]) -> Dict[str, Any]:
    swap = node.get("swap") or {}
    intent = swap.get("swapIntent") or {}
    args = swap.get("executionArgs") or {}
    return {
        "type": "swap",
        "protocolId": intent.get("protocolId"),
        "poolId": intent.get("poolId"),
        "tokenIn": intent.get("tokenIn"),
        "tokenInDecimals": intent.get("tokenInDecimals"),
        "tokenOut": intent.get("tokenOut"),
        "tokenOutDecimals": intent.get("tokenOutDecimals"),
        "amountInBig": intent.get("amountInBig"),
        "amountOutBig": intent.get("amountOutBig"),
        "isAmountIn": args.get("isAmountIn"),
        "zeroForOne": args.get("zeroForOne"),
        "recipient": args.get("recipient"),
        "recipientType": args.get("recipientType"),
    }


def _transfer_row_data(node: Dict[str, Any]) -> Dict[str, Any]:
    transfer = node.get("transfer") or {}
    return {
        "type": "transfer",
        "tokenId": transfer.get("tokenId"),
        "to": transfer.get("to"),
        "amount": transfer.get("amount"),
    }


def _table_label(title: str, rows: List[Tuple[str, Any]]) -> str:
    parts = [
        "<table>",
        f"<tr><th colspan='2' align='left'>{_escape(title)}</th></tr>",
    ]
    for key, value in rows:
        parts.append(
            "<tr>"
            f"<td align='right'>{_escape(key)}</td>"
            f"<td align='left' style='padding-left:2ch'>{_escape(_fmt_value(value))}</td>"
            "</tr>"
        )
    parts.append("</table>")
    return "".join(parts)


def _node_to_mermaid(node: Dict[str, Any]) -> Tuple[str, str]:
    node_type = node.get("type") or "unknown"
    if node_type == "swap":
        data = _swap_row_data(node)
        rows: List[Tuple[str, Any]] = []
        for field in SWAP_FIELDS:
            if field == "tokenIn":
                decimals = data.get("tokenInDecimals")
                token_in = data.get("tokenIn")
                value = (
                    f"{token_in} (decimals {decimals})"
                    if token_in is not None and decimals is not None
                    else token_in
                )
                rows.append(("tokenIn", value))
                continue
            if field == "tokenOut":
                decimals = data.get("tokenOutDecimals")
                token_out = data.get("tokenOut")
                value = (
                    f"{token_out} (decimals {decimals})"
                    if token_out is not None and decimals is not None
                    else token_out
                )
                rows.append(("tokenOut", value))
                continue
            rows.append((field, data.get(field)))
        label = _table_label("swap", rows)
        return label, "swap"

    if node_type == "transfer":
        data = _transfer_row_data(node)
        rows = [(field, data.get(field)) for field in TRANSFER_FIELDS]
        label = _table_label("transfer", rows)
        return label, "transfer"

    rows = [("type", node_type)]
    label = _table_label(node_type, rows)
    return label, "unknown"


def _walk(
    node: Dict[str, Any],
    nodes: List[str],
    edges: List[Tuple[str, str]],
    classes: Dict[str, str],
) -> str:
    node_id = f"N{len(nodes) + 1}"
    label, cls = _node_to_mermaid(node)
    nodes.append(f'  {node_id}["{label}"]')
    classes[node_id] = cls
    for child in node.get("callback", []) or []:
        child_id = _walk(child, nodes, edges, classes)
        edges.append((node_id, child_id))
    return node_id


def build_mermaid_dag(ir: Dict[str, Any]) -> str:
    root = ir.get("rootTrace")
    if not isinstance(root, dict):
        raise ValueError("IR JSON missing rootTrace")

    nodes: List[str] = []
    edges: List[Tuple[str, str]] = []
    classes: Dict[str, str] = {}

    _walk(root, nodes, edges, classes)

    lines = ["graph TD"]
    lines.extend(nodes)
    lines.append("")
    for src, dst in edges:
        lines.append(f"  {src} --> {dst}")
    lines.append("")
    lines.append(
        "  classDef swap fill:#d6ecff,stroke:#4a76a8,stroke-width:1px,color:#1f2a44;"
    )
    lines.append(
        "  classDef transfer fill:#ffe1e1,stroke:#b95c5c,stroke-width:1px,color:#3a1f1f;"
    )
    lines.append(
        "  classDef unknown fill:#eeeeee,stroke:#999999,stroke-width:1px,color:#333333;"
    )

    swap_nodes = [nid for nid, cls in classes.items() if cls == "swap"]
    transfer_nodes = [nid for nid, cls in classes.items() if cls == "transfer"]
    unknown_nodes = [nid for nid, cls in classes.items() if cls == "unknown"]
    if swap_nodes:
        lines.append(f"  class {','.join(swap_nodes)} swap;")
    if transfer_nodes:
        lines.append(f"  class {','.join(transfer_nodes)} transfer;")
    if unknown_nodes:
        lines.append(f"  class {','.join(unknown_nodes)} unknown;")

    return "\n".join(lines) + "\n"
