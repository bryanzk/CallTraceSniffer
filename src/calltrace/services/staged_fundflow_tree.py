"""分阶段资金树服务（通用规则 + 模板增强）。"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.request import Request, urlopen

WETH_ADDRESS = "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"
ETH_ADDRESS = "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"

STABLE_TOKENS = {
    "USDC",
    "USDT",
    "DAI",
    "USDS",
    "PYUSD",
    "CRVUSD",
    "USD3",
    "USDE",
    "USDAF",
    "EUSD",
    "REUSD",
    "FXUSD",
    "SCRVUSD",
    "SUSDS",
    "SUSDE",
    "SDOLA",
    "DOLA",
    "IUSD",
}

COLLATERAL_TOKENS = {
    "WETH",
    "WBTC",
    "TBTC",
    "CBBTC",
    "PAXG",
    "XAUT",
    "ETH+",
}

LABEL_MAP = {
    "Source": "资金来源",
    "SwapCycle": "卖出换债务币",
    "LiquidationLike": "清算执行",
    "TipSettlement": "支付 Builder Tip",
    "ProfitReturn": "利润回流",
    "Other": "资产归并",
}

METHOD_SELECTOR_MAP = {
    "5c38449e": "flashLoan",
    "2e1a7d4d": "withdraw",
    "022c0d9f": "swap",
    "128acb08": "swap",
    "a9059cbb": "transfer",
    "23b872dd": "transferFrom",
}

KNOWN_BORROW_ADDRS = {
    "0xba12222222228d8ba445958a75a0704d566bf2c8",  # Balancer Vault
}


@dataclass
class NormalizedTransfer:
    step: int
    from_addr: str
    to_addr: str
    token: str
    token_address: str
    amount: str
    frame_id: str


def _normalize_addr(value: Any) -> str:
    return (value or "").strip().lower()


def _parse_amount(value: Any) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError):
        return Decimal("0")


def _fmt_amount(value: str) -> str:
    amt = _parse_amount(value)
    txt = format(amt.normalize(), "f")
    if "." in txt:
        int_part, dec_part = txt.split(".", 1)
        dec_part = dec_part.rstrip("0")
        if dec_part:
            return f"{int(int_part):,}.{dec_part}"
    return f"{int(txt):,}"


def _short_addr(addr: str) -> str:
    if not addr or len(addr) < 12:
        return addr or "N/A"
    return f"{addr[:6]}...{addr[-4:]}"


def _extract_transaction(payload: Dict[str, Any]) -> Dict[str, Any]:
    result = payload.get("result")
    if not isinstance(result, list) or not result:
        raise ValueError("输入缺少 result 或 result 为空")
    first = result[0]
    tx = first.get("transaction")
    if not isinstance(tx, dict):
        raise ValueError("result[0].transaction 缺失或非 object")
    if "transfers" not in tx and isinstance(first.get("transfers"), list):
        tx = dict(tx)
        tx["transfers"] = first.get("transfers")
    return tx


def load_tx_payload(
    tx_hash: str,
    input_json: Optional[Path],
    fetch: bool,
    cache_dir: Path,
    read_cache: bool = True,
    write_cache: bool = True,
) -> Dict[str, Any]:
    """加载交易 payload。优先本地，其次可选联网。"""
    tx_hash = _normalize_addr(tx_hash)
    if not tx_hash.startswith("0x") or len(tx_hash) != 66:
        raise ValueError("tx_hash 格式非法")

    if input_json is not None:
        data = json.loads(input_json.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("输入 JSON 顶层必须是 object")
        return data

    cache_path = cache_dir / f"{tx_hash}_eigenphi_analyseTransaction.json"
    if read_cache and cache_path.exists():
        return json.loads(cache_path.read_text(encoding="utf-8"))

    if not fetch:
        raise ValueError(
            f"本地未找到该交易的 analyseTransaction 数据（{cache_path.name} 不存在）。"
            "请传 input_json 指定 JSON 路径，或将 fetch 设为 true 由服务端联网拉取。"
        )

    url = (
        "https://eigenphi.io/api/v1/analyseTransaction"
        f"?chain=ALL&enableCallStack=on&tx={tx_hash}"
    )
    req = Request(url=url, headers={"accept": "*/*", "user-agent": "Mozilla/5.0"})
    with urlopen(req, timeout=30) as resp:  # nosec B310
        body = resp.read().decode("utf-8")
    data = json.loads(body)
    if write_cache:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return data


def _normalize_transfer(raw: Dict[str, Any]) -> Optional[NormalizedTransfer]:
    step = raw.get("transferStep")
    if step is None:
        return None
    token = raw.get("token") or {}
    return NormalizedTransfer(
        step=int(step),
        from_addr=_normalize_addr(raw.get("from")),
        to_addr=_normalize_addr(raw.get("to")),
        token=(token.get("symbol") or "UNKNOWN").upper(),
        token_address=_normalize_addr(token.get("address")),
        amount=str(raw.get("amount", "0")),
        frame_id=str(raw.get("frameId") or ""),
    )


def _group_transfers_by_frame_id(transfers: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for item in transfers:
        norm = _normalize_transfer(item)
        if norm is None:
            continue
        grouped.setdefault(norm.frame_id, []).append(
            {
                "transferStep": norm.step,
                "from": norm.from_addr,
                "to": norm.to_addr,
                "token": norm.token,
                "tokenAddress": norm.token_address,
                "amount": norm.amount,
            }
        )
    for fid, rows in grouped.items():
        rows.sort(key=lambda x: x["transferStep"])
    return grouped


def _build_node(
    frame: Dict[str, Any],
    transfers_by_frame: Dict[str, List[Dict[str, Any]]],
    include_static: bool,
    prune: bool,
) -> Optional[Dict[str, Any]]:
    frame_id = str(frame.get("frameId") or "")
    call_type = str(frame.get("type") or "").upper()
    if not include_static and call_type == "STATICCALL":
        return None

    node = {
        "frameId": frame_id,
        "type": frame.get("type"),
        "from": _normalize_addr(frame.get("from")),
        "to": _normalize_addr(frame.get("to")),
        "methodNames": frame.get("methodNames") or [],
        "value": frame.get("value"),
        "transferCount": int(frame.get("transferCount") or 0),
        "transfers": transfers_by_frame.get(frame_id, []),
        "children": [],
    }

    for child in frame.get("children") or []:
        built = _build_node(child, transfers_by_frame, include_static, prune)
        if built is not None:
            node["children"].append(built)

    if prune and frame_id != "0" and node["transferCount"] == 0 and not node["children"]:
        return None
    return node


def build_flow_tree(
    transaction: Dict[str, Any],
    include_static: bool = True,
    prune: bool = True,
) -> Dict[str, Any]:
    """从 transaction 构建 frame->transfer 对齐后的执行树。"""
    call_stack = transaction.get("callStack")
    if not isinstance(call_stack, dict):
        raise ValueError("transaction.callStack 缺失或非 object")

    transfers = transaction.get("transfers") or []
    by_frame = _group_transfers_by_frame_id(transfers)
    root = _build_node(call_stack, by_frame, include_static, prune)
    if root is None:
        raise ValueError("callStack 根节点构建失败")

    return {
        "tx_hash": _normalize_addr(transaction.get("transactionHash")),
        "from": _normalize_addr(transaction.get("from")),
        "to": _normalize_addr(transaction.get("to")),
        "root": root,
    }


def _resolve_executor(flow_tree: Dict[str, Any], tx_meta: Dict[str, Any], transfers: List[NormalizedTransfer]) -> str:
    tx_to = _normalize_addr(tx_meta.get("to") or flow_tree.get("to"))
    if tx_to:
        return tx_to

    score: Dict[str, int] = defaultdict(int)
    for t in transfers:
        score[t.from_addr] += 1
        score[t.to_addr] += 1
    if not score:
        return _normalize_addr(tx_meta.get("from"))
    return sorted(score.items(), key=lambda x: (-x[1], x[0]))[0][0]


def _classify_stage_type(
    idx: int,
    transfers: List[NormalizedTransfer],
    executor: str,
    sender: str,
    builder: str,
) -> tuple[str, str]:
    t = transfers[idx]

    if (
        t.token == "WETH"
        and t.from_addr == executor
        and t.to_addr == WETH_ADDRESS
    ):
        return "TipSettlement", "weth_to_weth_contract"
    if (
        t.token == "ETH"
        and t.from_addr == WETH_ADDRESS
        and t.to_addr == executor
    ):
        return "TipSettlement", "eth_unwrap_back"
    if (
        t.token == "ETH"
        and t.from_addr == executor
        and builder
        and t.to_addr == builder
    ):
        return "TipSettlement", "eth_to_builder"
    if (
        t.token == "ETH"
        and t.from_addr == executor
        and sender
        and t.to_addr == sender
    ):
        return "ProfitReturn", "eth_to_sender"

    first_in = next((x for x in transfers if x.to_addr == executor and x.from_addr != executor), None)
    if first_in and t.step == first_in.step:
        return "Source", "first_inbound_to_executor"

    if t.to_addr == executor and t.token in COLLATERAL_TOKENS and idx > 0:
        prev = transfers[idx - 1]
        if prev.from_addr == executor and prev.token in STABLE_TOKENS and (t.step - prev.step) <= 2:
            return "LiquidationLike", "stable_out_then_collateral_in"

    if t.from_addr == executor or t.to_addr == executor:
        return "SwapCycle", "executor_involved"

    return "Other", "fallback"


def _stage_label(stage_type: str, rules_matched: List[str]) -> str:
    if stage_type == "LiquidationLike" and "stable_out_then_collateral_in" in rules_matched:
        return "清算执行（还债取抵押）"
    return LABEL_MAP.get(stage_type, "资产归并")


def _direction(flow: NormalizedTransfer, executor: str) -> str:
    if flow.from_addr == executor and flow.to_addr == executor:
        return "internal"
    if flow.from_addr == executor:
        return "out"
    if flow.to_addr == executor:
        return "in"
    return "internal"


def _compress_steps(steps: List[int]) -> str:
    if not steps:
        return "[#?]"
    steps = sorted(set(steps))
    if len(steps) == 1:
        return f"[#{steps[0]}]"
    # 连续区间压缩
    if steps == list(range(steps[0], steps[-1] + 1)):
        return f"[#{steps[0]}-#{steps[-1]}]"
    return "[" + ",".join(f"#{x}" for x in steps) + "]"


def build_staged_fundflow_tree(
    flow_tree: Dict[str, Any],
    transfers: List[Dict[str, Any]],
    address_meta: Dict[str, Any],
    tx_meta: Dict[str, Any],
) -> Dict[str, Any]:
    """构建分阶段资金树（结构化 JSON）。"""
    del address_meta  # 当前版本不依赖地址元数据

    normalized: List[NormalizedTransfer] = []
    for raw in transfers:
        norm = _normalize_transfer(raw)
        if norm is not None:
            normalized.append(norm)
    normalized.sort(key=lambda x: x.step)

    sender = _normalize_addr(tx_meta.get("from") or flow_tree.get("from"))
    builder = _normalize_addr(tx_meta.get("miner"))
    executor = _resolve_executor(flow_tree, tx_meta, normalized)

    # 仅保留与 executor 强相关的资金流
    relevant = [t for t in normalized if t.from_addr == executor or t.to_addr == executor or (t.token == "ETH" and t.to_addr in {builder, sender})]

    stages: List[Dict[str, Any]] = []
    current: Optional[Dict[str, Any]] = None

    for idx, transfer in enumerate(relevant):
        stage_type, reason = _classify_stage_type(idx, relevant, executor, sender, builder)
        if current is None or current["stage_type"] != stage_type or transfer.step - current["step_range"][1] > 2:
            if current is not None:
                current["stage_label"] = _stage_label(current["stage_type"], current["rules_matched"])
                stages.append(current)
            current = {
                "stage_id": f"S{len(stages) + 1}",
                "stage_type": stage_type,
                "stage_label": "",
                "step_range": [transfer.step, transfer.step],
                "rules_matched": [reason],
                "flows": [],
                "net_changes": [],
            }
        else:
            current["step_range"][1] = transfer.step
            if reason not in current["rules_matched"]:
                current["rules_matched"].append(reason)

        current["flows"].append(
            {
                "step": transfer.step,
                "from": transfer.from_addr,
                "to": transfer.to_addr,
                "token": transfer.token,
                "amount": transfer.amount,
                "frame_id": transfer.frame_id,
                "direction": _direction(transfer, executor),
            }
        )

    if current is not None:
        current["stage_label"] = _stage_label(current["stage_type"], current["rules_matched"])
        stages.append(current)

    # Tip 阶段必须包含给 builder 的 ETH 转账；否则按普通换汇处理。
    for stage in stages:
        if stage["stage_type"] == "TipSettlement" and "eth_to_builder" not in stage["rules_matched"]:
            stage["stage_type"] = "SwapCycle"
            stage["rules_matched"] = [x for x in stage["rules_matched"] if x != "eth_to_builder"]
            stage["stage_label"] = _stage_label(stage["stage_type"], stage["rules_matched"])

    for stage in stages:
        net: Dict[str, Decimal] = defaultdict(Decimal)
        for flow in stage["flows"]:
            amt = _parse_amount(flow["amount"])
            if flow["direction"] == "in":
                net[flow["token"]] += amt
            elif flow["direction"] == "out":
                net[flow["token"]] -= amt
        stage["net_changes"] = [
            {"token": token, "net_amount": format(value.normalize(), "f")}
            for token, value in sorted(net.items())
            if value != 0
        ]

    token_views_map: Dict[str, Dict[str, Any]] = {}
    for stage in stages:
        for flow in stage["flows"]:
            token = flow["token"]
            entry = token_views_map.setdefault(token, {"token": token, "stage_ids": [], "flows": []})
            if stage["stage_id"] not in entry["stage_ids"]:
                entry["stage_ids"].append(stage["stage_id"])
            entry["flows"].append({**flow, "stage_id": stage["stage_id"]})

    token_views = sorted(
        token_views_map.values(),
        key=lambda x: min((f["step"] for f in x["flows"]), default=10**9),
    )

    return {
        "tx_hash": _normalize_addr(tx_meta.get("tx_hash") or flow_tree.get("tx_hash")),
        "executor": executor,
        "sender": sender,
        "builder": builder,
        "stages": stages,
        "token_views": token_views,
        "summary": {
            "transfer_count": len(relevant),
            "stage_count": len(stages),
            "tokens": [x["token"] for x in token_views],
        },
    }


def render_staged_tree_markdown(staged_tree: Dict[str, Any], style: str = "example") -> str:
    """将阶段化结构渲染为示例风格 Markdown。"""
    if style != "example":
        raise ValueError("仅支持 example 风格")

    lines: List[str] = []
    lines.append(f"# Tx {_short_addr(staged_tree.get('tx_hash', ''))} 分阶段资金树")
    lines.append("")
    lines.append(f"- Executor: `{staged_tree.get('executor', '')}`")
    lines.append(f"- Sender: `{staged_tree.get('sender', '')}`")
    lines.append(f"- Builder: `{staged_tree.get('builder', '')}`")
    lines.append("")

    stage_map = {s["stage_id"]: s for s in staged_tree.get("stages", [])}

    for token_view in staged_tree.get("token_views", []):
        token = token_view["token"]
        lines.append(token)
        for sid in token_view.get("stage_ids", []):
            stage = stage_map.get(sid)
            if not stage:
                continue
            flows = [f for f in token_view.get("flows", []) if f.get("stage_id") == sid]
            if not flows:
                continue

            lines.append(f"└─[{stage['stage_label']}]")

            grouped: Dict[tuple, List[Dict[str, Any]]] = defaultdict(list)
            for flow in flows:
                key = (flow["from"], flow["to"], flow["amount"])
                grouped[key].append(flow)

            for (from_addr, to_addr, amount), rows in grouped.items():
                steps = [r["step"] for r in rows]
                step_ref = _compress_steps(steps)
                lines.append(
                    f"  └─ {_short_addr(from_addr)} ─({token} {_fmt_amount(amount)})→ {_short_addr(to_addr)} {step_ref}"
                )
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def _extract_tx_and_context(payload: Dict[str, Any]) -> tuple[Dict[str, Any], Dict[str, Any]]:
    tx = _extract_transaction(payload)
    result = payload.get("result")
    result0 = result[0] if isinstance(result, list) and result else {}
    return tx, result0 if isinstance(result0, dict) else {}


def _collect_call_events(node: Dict[str, Any], out: List[Dict[str, Any]]) -> None:
    out.append(
        {
            "frame_id": str(node.get("frameId") or ""),
            "from": _normalize_addr(node.get("from")),
            "to": _normalize_addr(node.get("to")),
            "selector": (node.get("fourBytes") or "").lower(),
            "type": (node.get("type") or "").upper(),
            "transfer_steps": [int(x) for x in (node.get("transferSteps") or []) if isinstance(x, int)],
        }
    )
    for child in node.get("children") or []:
        if isinstance(child, dict):
            _collect_call_events(child, out)


def _build_step_to_call_map(call_events: List[Dict[str, Any]]) -> Dict[int, Dict[str, Any]]:
    by_step: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
    for event in call_events:
        for step in event["transfer_steps"]:
            by_step[step].append(event)

    resolved: Dict[int, Dict[str, Any]] = {}
    for step, events in by_step.items():
        # 优先最深 frame（路径更具体）
        resolved[step] = sorted(events, key=lambda x: (-x["frame_id"].count("_"), x["frame_id"]))[0]
    return resolved


def _dynamic_stage_type(
    idx: int,
    transfer: NormalizedTransfer,
    all_transfers: List[NormalizedTransfer],
    executor: str,
    sender: str,
    builder: str,
    protocol_addrs: set[str],
) -> tuple[str, List[str]]:
    rules: List[str] = []
    token = transfer.token

    if transfer.to_addr == executor and transfer.from_addr in KNOWN_BORROW_ADDRS and token in STABLE_TOKENS:
        rules.append("borrow_in_from_known_lender")
        return "Borrow", rules

    if (
        token == "ETH"
        and transfer.from_addr == executor
        and builder
        and transfer.to_addr == builder
    ):
        rules.append("eth_to_builder")
        return "Tip", rules
    if token == "WETH" and transfer.from_addr == executor and transfer.to_addr == WETH_ADDRESS:
        rules.append("weth_to_contract")
        return "Tip", rules
    if token == "ETH" and transfer.from_addr == WETH_ADDRESS and transfer.to_addr == executor:
        rules.append("eth_unwrap")
        return "Tip", rules

    if transfer.from_addr == executor and sender and transfer.to_addr == sender:
        rules.append("payout_to_sender")
        return "Profit", rules
    if (
        transfer.from_addr == executor
        and transfer.token in STABLE_TOKENS
        and transfer.to_addr not in protocol_addrs
        and transfer.to_addr not in {builder, sender, WETH_ADDRESS}
        and idx >= max(0, len(all_transfers) - 3)
    ):
        rules.append("tail_stable_payout_to_external")
        return "Profit", rules

    if transfer.from_addr == executor and transfer.to_addr in KNOWN_BORROW_ADDRS and token in STABLE_TOKENS:
        rules.append("repay_to_known_lender")
        return "Repay", rules

    if token.upper().startswith("VARIABLEDEBT"):
        rules.append("variable_debt_burn")
        return "Liquidation", rules

    if token.upper().startswith("SP"):
        rules.append("sp_token_adjust")
        return "Liquidation", rules

    if transfer.to_addr == executor and token in COLLATERAL_TOKENS:
        prev = all_transfers[idx - 1] if idx > 0 else None
        if prev and prev.from_addr == executor and prev.token in STABLE_TOKENS:
            rules.append("stable_out_then_collateral_in")
            return "Liquidation", rules

    if transfer.from_addr == executor or transfer.to_addr == executor:
        if token in STABLE_TOKENS or token in COLLATERAL_TOKENS or token in {"WETH", "ETH", "USDC", "USDT"}:
            rules.append("token_exchange_pattern")
            return "Swap", rules
        rules.append("weak_evidence_unknown_token")
        return "Other", rules

    rules.append("weak_evidence")
    return "Other", rules


def _phase_confidence(phase: Dict[str, Any]) -> float:
    rules = phase.get("rules_matched") or []
    score = 0.45
    score += min(0.25, 0.06 * len(rules))

    actions = phase.get("actions") or []
    mapped_selectors = 0
    for action in actions:
        selector = (action.get("call_context", {}) or {}).get("selector") or ""
        if selector in METHOD_SELECTOR_MAP:
            mapped_selectors += 1
    if actions:
        score += min(0.2, 0.05 * mapped_selectors)

    if phase.get("phase_type") in {"Borrow", "Repay", "Tip", "Profit"}:
        score += 0.12
    if phase.get("phase_type") == "Other":
        score -= 0.1

    score = max(0.0, min(0.99, score))
    return round(score, 3)


def _dynamic_phase_label(phase_type: str, phase: Dict[str, Any]) -> str:
    net = phase.get("net_changes") or []
    dominant = net[0]["token"] if net else ""

    if phase_type == "Borrow":
        return f"闪电借入阶段（{dominant or '主资产'}）"
    if phase_type == "Repay":
        return f"借款归还阶段（{dominant or '主资产'}）"
    if phase_type == "Liquidation":
        return "清算执行阶段（还债取抵押）"
    if phase_type == "Swap":
        return "多池换汇阶段"
    if phase_type == "Settlement":
        return "内部结算阶段"
    if phase_type == "Tip":
        return "Builder 支付阶段（WETH 解包）"
    if phase_type == "Profit":
        return f"利润回流阶段（{dominant or '收益资产'}）"
    return "其他阶段（证据不足）"


def _dynamic_phase_intent(phase_type: str) -> str:
    intent_map = {
        "Borrow": "获取短时流动性以启动策略路径",
        "Repay": "回补借入资产并关闭借贷敞口",
        "Liquidation": "执行清算并换取可处置抵押资产",
        "Swap": "通过多池换汇重平衡头寸",
        "Settlement": "进行内部资产净额结算",
        "Tip": "支付 Builder/coinbase 维持打包优先级",
        "Profit": "将净收益转移至收益地址",
        "Other": "无法稳定归类，保留为观察阶段",
    }
    return intent_map.get(phase_type, "未定义业务意图")


def _normalize_transfers_from_tx(tx: Dict[str, Any]) -> List[NormalizedTransfer]:
    out: List[NormalizedTransfer] = []
    for raw in tx.get("transfers") or []:
        norm = _normalize_transfer(raw)
        if norm is not None:
            out.append(norm)
    out.sort(key=lambda x: x.step)
    return out


def build_dynamic_semantic_tree(payload: dict, tx_hash: str, strict: bool = True) -> dict:
    """构建交易自适应语义执行结构树。"""
    tx, _result0 = _extract_tx_and_context(payload)
    normalized = _normalize_transfers_from_tx(tx)
    call_events: List[Dict[str, Any]] = []
    call_stack = tx.get("callStack") or {}
    if not isinstance(call_stack, dict):
        raise ValueError("transaction.callStack 缺失或非 object")
    _collect_call_events(call_stack, call_events)
    step_to_call = _build_step_to_call_map(call_events)
    protocol_addrs = {e.get("to", "") for e in call_events if e.get("to")}

    flow_tree = build_flow_tree(tx, include_static=False, prune=True)
    executor = _resolve_executor(flow_tree, {"to": tx.get("to"), "from": tx.get("from")}, normalized)
    sender = _normalize_addr(tx.get("from"))
    builder = _normalize_addr(tx.get("miner"))

    if not normalized:
        return {
            "tx_hash": _normalize_addr(tx_hash),
            "root_actor": f"EOA / Liquidator {_short_addr(executor)}",
            "root_call_target": f"CALL {_short_addr(tx.get('to') or executor)}",
            "phases": [],
            "summary": {"phase_count": 0, "transfer_count": 0},
        }

    phases: List[Dict[str, Any]] = []
    current: Optional[Dict[str, Any]] = None

    for idx, t in enumerate(normalized):
        stage_type, rules = _dynamic_stage_type(
            idx,
            t,
            normalized,
            executor,
            sender,
            builder,
            protocol_addrs,
        )
        call_ctx = step_to_call.get(t.step, {})
        domain = call_ctx.get("frame_id", "").split("_")[:2]
        domain_id = "_".join(domain) if domain else ""

        boundary_score = 0
        if current is not None:
            if stage_type != current["phase_type"]:
                boundary_score += 2
            if t.step - current["step_range"][1] > 2:
                boundary_score += 1
            if domain_id and domain_id != current.get("domain_id"):
                boundary_score += 1

        if current is None or boundary_score >= 2:
            if current is not None:
                phases.append(current)
            current = {
                "phase_id": f"P{len(phases) + 1}",
                "phase_type": stage_type,
                "phase_label": "",
                "step_range": [t.step, t.step],
                "domain_id": domain_id,
                "rules_matched": list(rules),
                "actions": [],
                "net_changes": [],
                "confidence": 0.0,
                "inferred": False,
            }
        else:
            current["step_range"][1] = t.step
            for rule in rules:
                if rule not in current["rules_matched"]:
                    current["rules_matched"].append(rule)

        method_name = METHOD_SELECTOR_MAP.get((call_ctx.get("selector") or "").lower(), "")
        action_type = method_name or stage_type.lower()

        current["actions"].append(
            {
                "action_type": action_type,
                "call_context": {
                    "frame_id": call_ctx.get("frame_id", t.frame_id),
                    "from": call_ctx.get("from", ""),
                    "to": call_ctx.get("to", ""),
                    "selector": call_ctx.get("selector", ""),
                    "method": method_name,
                },
                "transfers": [
                    {
                        "step": t.step,
                        "from": t.from_addr,
                        "to": t.to_addr,
                        "token": t.token,
                        "amount": t.amount,
                    }
                ],
            }
        )

    if current is not None:
        phases.append(current)

    for phase in phases:
        net: Dict[str, Decimal] = defaultdict(Decimal)
        for action in phase["actions"]:
            for tf in action["transfers"]:
                token = tf["token"]
                amt = _parse_amount(tf["amount"])
                if tf["from"] == executor:
                    net[token] -= amt
                if tf["to"] == executor:
                    net[token] += amt
        phase["net_changes"] = [
            {"token": token, "net_amount": format(v.normalize(), "f")}
            for token, v in sorted(net.items(), key=lambda x: abs(x[1]), reverse=True)
            if v != 0
        ]
        phase["top_flows"] = []
        for action in phase["actions"][:3]:
            for tf in action.get("transfers", [])[:1]:
                phase["top_flows"].append(
                    {
                        "step": tf.get("step"),
                        "from": tf.get("from"),
                        "to": tf.get("to"),
                        "token": tf.get("token"),
                        "amount": tf.get("amount"),
                    }
                )
        phase["confidence"] = _phase_confidence(phase)
        phase["inferred"] = phase["confidence"] < 0.7
        weak_only = set(phase.get("rules_matched") or []) <= {"weak_evidence", "weak_evidence_unknown_token"}
        if strict and phase["inferred"] and weak_only and phase["phase_type"] not in {"Tip", "Profit"}:
            phase["phase_type"] = "Other"
        phase["phase_label"] = _dynamic_phase_label(phase["phase_type"], phase)
        phase["phase_intent"] = _dynamic_phase_intent(phase["phase_type"])
        rules_txt = ",".join(phase.get("rules_matched") or [])
        step_range = phase.get("step_range") or []
        step_text = f"#{step_range[0]}-#{step_range[1]}" if len(step_range) == 2 else "#?"
        phase["evidence_summary"] = f"steps={step_text}; rules={rules_txt}; confidence={phase['confidence']:.3f}"

    # Root 主调用目标：优先第一条 executor -> 非系统合约转出
    root_call_target = _normalize_addr(tx.get("to")) or executor
    for t in normalized:
        if t.from_addr == executor and t.to_addr not in {WETH_ADDRESS, builder, sender}:
            root_call_target = t.to_addr
            break

    return {
        "tx_hash": _normalize_addr(tx_hash or tx.get("transactionHash")),
        "root_actor": f"EOA / Liquidator {executor}",
        "root_call_target": f"CALL {root_call_target}",
        "phases": phases,
        "summary": {
            "phase_count": len(phases),
            "transfer_count": len(normalized),
        },
    }


def render_dynamic_semantic_markdown(tree: dict) -> str:
    """渲染动态语义执行结构树 Markdown。"""
    lines: List[str] = []
    lines.append(f"Tx {_short_addr(tree.get('tx_hash', ''))}")
    lines.append(f"└─ {tree.get('root_actor', '')}")
    lines.append(f"   └─ {tree.get('root_call_target', '')}")

    for idx, phase in enumerate(tree.get("phases", []), start=1):
        inferred = " (推断)" if phase.get("inferred") else ""
        lines.append(
            f"      ├─ [阶段{idx}] {phase.get('phase_label', '')}{inferred} "
            f"(confidence={phase.get('confidence', 0):.3f}, steps=#{phase['step_range'][0]}-#{phase['step_range'][1]})"
        )
        for action in phase.get("actions", []):
            ctx = action.get("call_context", {})
            selector = ctx.get("selector") or "N/A"
            method = ctx.get("method") or selector
            lines.append(
                f"      │  └─ CALL {_short_addr(ctx.get('to', ''))} {method}"
            )
            for tf in action.get("transfers", []):
                lines.append(
                    f"      │     └─ {_short_addr(tf['from'])} ─({tf['token']} {_fmt_amount(tf['amount'])})→ "
                    f"{_short_addr(tf['to'])} [#{tf['step']}]"
                )
    lines.append("")
    return "\n".join(lines)


__all__ = [
    "load_tx_payload",
    "build_flow_tree",
    "build_staged_fundflow_tree",
    "render_staged_tree_markdown",
    "build_dynamic_semantic_tree",
    "render_dynamic_semantic_markdown",
]
