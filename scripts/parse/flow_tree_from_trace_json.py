#!/usr/bin/env python3
"""
从 BlockSec/EigenPhi 风格 trace JSON 生成「资金流执行结构树」。

输入：完整 API 响应 JSON（含 status, result）。
result[0].transaction 需包含 callStack（树形调用栈）与 transfers（扁平转账列表）。

输出：树形 JSON，每节点含 frameId/type/from/to/transfers[]/children[]，
其中 transfers 仅包含该 frameId 对应的转账。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def _load_json(path: Optional[Path], stdin_fallback: bool = False) -> Dict[str, Any]:
    if path is not None and path.exists():
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    elif stdin_fallback:
        data = json.load(sys.stdin)
    else:
        raise ValueError("需要 --input 或从 stdin 传入 JSON")
    if not isinstance(data, dict):
        raise ValueError("输入 JSON 顶层必须是 object")
    return data


def _get_transaction(data: Dict[str, Any]) -> Dict[str, Any]:
    """从 API 响应取出 result[0].transaction。"""
    result = data.get("result")
    if not isinstance(result, list) or len(result) == 0:
        raise ValueError("输入缺少 result 或 result 为空")
    tx = result[0].get("transaction")
    if not isinstance(tx, dict):
        raise ValueError("result[0].transaction 缺失或非 object")
    return tx


def _normalize_transfer(t: Dict[str, Any]) -> Dict[str, Any]:
    """将原始 transfer 规范化为简洁字段。"""
    token = t.get("token") or {}
    return {
        "transferStep": t.get("transferStep"),
        "from": (t.get("from") or "").lower(),
        "to": (t.get("to") or "").lower(),
        "token": token.get("symbol") or "?",
        "tokenAddress": (token.get("address") or "").lower(),
        "amount": t.get("amount"),
        "category": t.get("category") or t.get("typeName") or "",
    }


def _group_transfers_by_frame_id(transfers: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """按 frameId 分组，每组按 transferStep 排序。"""
    by_frame: Dict[str, List[Dict[str, Any]]] = {}
    for t in transfers:
        fid = t.get("frameId") or ""
        by_frame.setdefault(fid, []).append(_normalize_transfer(t))
    for fid in by_frame:
        by_frame[fid].sort(key=lambda x: (x.get("transferStep") is None, x.get("transferStep")))
    return by_frame


def _build_node(
    frame: Dict[str, Any],
    transfers_by_frame: Dict[str, List[Dict[str, Any]]],
    include_static: bool,
    prune: bool,
) -> Optional[Dict[str, Any]]:
    """递归构建单节点，挂载 transfers，可选剪枝。"""
    frame_id = frame.get("frameId") or ""
    call_type = (frame.get("type") or "").upper()
    if not include_static and call_type == "STATICCALL":
        return None

    node: Dict[str, Any] = {
        "frameId": frame_id,
        "type": frame.get("type"),
        "from": (frame.get("from") or "").lower(),
        "to": (frame.get("to") or "").lower(),
        "methodNames": frame.get("methodNames") or [],
        "value": frame.get("value"),
        "transferCount": frame.get("transferCount", 0),
        "transfers": transfers_by_frame.get(frame_id, []),
        "children": [],
    }

    children = frame.get("children") or []
    for ch in children:
        child_node = _build_node(ch, transfers_by_frame, include_static, prune)
        if child_node is not None:
            node["children"].append(child_node)

    if prune:
        # 后序剪枝：无转账且无子节点则移除（根节点不删）
        if frame_id != "0" and node["transferCount"] == 0 and len(node["children"]) == 0:
            return None

    return node


def build_flow_tree(
    transaction: Dict[str, Any],
    *,
    include_static: bool = True,
    prune: bool = False,
) -> Dict[str, Any]:
    """从 transaction（含 callStack + transfers）构建资金流执行结构树。"""
    call_stack = transaction.get("callStack")
    if not isinstance(call_stack, dict):
        raise ValueError("transaction.callStack 缺失或非 object")

    transfers = transaction.get("transfers") or []
    transfers_by_frame = _group_transfers_by_frame_id(transfers)

    root_node = _build_node(call_stack, transfers_by_frame, include_static, prune)
    if root_node is None:
        raise ValueError("callStack 根节点构建失败")

    tx_hash = (transaction.get("transactionHash") or "").strip()
    from_addr = (transaction.get("from") or "").strip()
    to_addr = (transaction.get("to") or "").strip()

    return {
        "tx_hash": tx_hash.lower() if tx_hash else "",
        "from": from_addr.lower() if from_addr else "",
        "to": to_addr.lower() if to_addr else "",
        "root": root_node,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="从 callStack+transfers 生成资金流执行结构树 JSON",
    )
    parser.add_argument(
        "--input",
        default="",
        help="输入 JSON 文件路径（含 status/result）；不指定则从 stdin 读取",
    )
    parser.add_argument(
        "--output",
        default="",
        help="输出 JSON 文件路径；不指定则打印到 stdout",
    )
    parser.add_argument(
        "--prune",
        action="store_true",
        help="剪枝：仅保留自身或后代存在转账的节点",
    )
    parser.add_argument(
        "--include-static",
        action="store_true",
        default=True,
        help="保留 STATICCALL 节点（默认保留）",
    )
    parser.add_argument(
        "--no-include-static",
        action="store_false",
        dest="include_static",
        help="不保留 STATICCALL 节点",
    )
    args = parser.parse_args()

    input_path = Path(args.input) if args.input else None
    data = _load_json(input_path, stdin_fallback=(input_path is None))
    transaction = _get_transaction(data)

    out = build_flow_tree(
        transaction,
        include_static=args.include_static,
        prune=args.prune,
    )

    json_str = json.dumps(out, ensure_ascii=False, indent=2)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json_str, encoding="utf-8")
        print(str(output_path))
    else:
        print(json_str)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
