"""分析师报告生成服务（代码优先，可选 LLM 润色）。"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List


def _parse_decimal(value: Any) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError):
        return Decimal("0")


def _fmt_decimal(value: Any) -> str:
    d = _parse_decimal(value)
    txt = format(d.normalize(), "f")
    if "." in txt:
        txt = txt.rstrip("0").rstrip(".")
    return txt


def _short(addr: str) -> str:
    if not addr:
        return "N/A"
    if len(addr) < 12:
        return addr
    return f"{addr[:6]}...{addr[-4:]}"


def _phase_narrative(phase: Dict[str, Any]) -> Dict[str, Any]:
    actions = phase.get("actions") or []
    all_transfers = []
    evidence_steps: List[int] = []
    key_amounts: List[str] = []

    for action in actions:
        for tf in action.get("transfers") or []:
            all_transfers.append(tf)
            step = tf.get("step")
            if isinstance(step, int):
                evidence_steps.append(step)
            key_amounts.append(f"{tf.get('token')} {_fmt_decimal(tf.get('amount'))}")

    confidence = float(phase.get("confidence") or 0)
    inferred = bool(phase.get("inferred"))
    confidence_text = f"confidence={confidence:.3f}"
    if inferred:
        confidence_text += "（推断）"

    phase_label = phase.get("phase_label") or phase.get("phase_type") or "未命名阶段"
    step_range = phase.get("step_range") or []
    if len(step_range) == 2:
        step_text = f"#{step_range[0]}-#{step_range[1]}"
    else:
        step_text = "#?"

    top3 = all_transfers[:3]
    flow_texts = [
        f"{_short(tf.get('from',''))} -> {_short(tf.get('to',''))} {tf.get('token')} {_fmt_decimal(tf.get('amount'))} [#{tf.get('step')}]"
        for tf in top3
    ]

    narrative = (
        f"该阶段识别为“{phase_label}”，覆盖步骤 {step_text}。"
        f"关键资金流：{'；'.join(flow_texts) if flow_texts else '无可用转账证据'}。"
    )

    return {
        "title": phase_label,
        "narrative": narrative,
        "confidence_text": confidence_text,
        "evidence_steps": sorted(set(evidence_steps)),
        "key_amounts": key_amounts[:5],
    }


def _extract_pnl_summary(tree: Dict[str, Any]) -> str:
    last_phase = (tree.get("phases") or [])[-1] if (tree.get("phases") or []) else {}
    last_actions = last_phase.get("actions") or []
    for action in reversed(last_actions):
        for tf in action.get("transfers") or []:
            if tf.get("from") and tf.get("token"):
                return f"可见末端转移：{tf.get('token')} {_fmt_decimal(tf.get('amount'))} -> {_short(tf.get('to',''))} [#{tf.get('step')}]"
    return "未识别到明确利润转移。"


def _build_risk_flags(tree: Dict[str, Any]) -> List[str]:
    flags: List[str] = []
    phases = tree.get("phases") or []
    low_conf = [p for p in phases if float(p.get("confidence") or 0) < 0.7]
    if low_conf:
        flags.append(f"存在低置信阶段 {len(low_conf)} 个，需人工复核。")

    unknown_calls = 0
    for p in phases:
        for action in p.get("actions") or []:
            method = ((action.get("call_context") or {}).get("method") or "").strip()
            if not method:
                unknown_calls += 1
    if unknown_calls:
        flags.append(f"存在未识别方法调用 {unknown_calls} 处。")

    max_jump = 0
    prev = None
    for p in phases:
        rng = p.get("step_range") or []
        if len(rng) != 2:
            continue
        if prev is not None:
            max_jump = max(max_jump, int(rng[0]) - int(prev))
        prev = int(rng[1])
    if max_jump > 5:
        flags.append("阶段间存在较大 step 跳变，可能含隐藏结算路径。")

    if not flags:
        flags.append("未发现显著结构性风险信号。")
    return flags


def build_analyst_report(tree: Dict[str, Any], style: str = "default") -> Dict[str, Any]:
    """从 dynamic semantic tree 构建分析师报告结构。"""
    if style != "default":
        raise ValueError("仅支持 default 风格")

    phases = tree.get("phases") or []
    phase_narratives = [_phase_narrative(p) for p in phases]
    risk_flags = _build_risk_flags(tree)

    summary = (
        f"交易 {tree.get('tx_hash','')} 共识别 {len(phases)} 个业务阶段，"
        f"执行主体为 {tree.get('root_actor','N/A')}。"
    )

    evidence_index = []
    for idx, p in enumerate(phases, start=1):
        evidence_index.append(
            {
                "phase": idx,
                "phase_type": p.get("phase_type"),
                "step_range": p.get("step_range"),
                "rules": p.get("rules_matched") or [],
            }
        )

    return {
        "tx_hash": tree.get("tx_hash", ""),
        "executive_summary": summary,
        "phase_narratives": phase_narratives,
        "pnl_summary": _extract_pnl_summary(tree),
        "risk_flags": risk_flags,
        "evidence_index": evidence_index,
    }


def render_analyst_markdown(report: Dict[str, Any]) -> str:
    """渲染分析师报告 Markdown。"""
    lines: List[str] = []
    lines.append(f"# Tx {report.get('tx_hash','')} 分析师报告")
    lines.append("")
    lines.append("## 执行摘要")
    lines.append(f"- {report.get('executive_summary','')}")
    lines.append("")
    lines.append("## 阶段解读")

    for idx, phase in enumerate(report.get("phase_narratives") or [], start=1):
        lines.append(f"### 阶段 {idx}: {phase.get('title','')}\n")
        lines.append(f"- 说明: {phase.get('narrative','')}")
        lines.append(f"- 置信度: {phase.get('confidence_text','')}")
        steps = phase.get("evidence_steps") or []
        if steps:
            step_text = ", ".join(f"#{x}" for x in steps)
            lines.append(f"- 证据步骤: {step_text}")
        amounts = phase.get("key_amounts") or []
        if amounts:
            lines.append(f"- 关键金额: {', '.join(amounts)}")
        lines.append("")

    lines.append("## PnL 摘要")
    lines.append(f"- {report.get('pnl_summary','')}")
    lines.append("")

    lines.append("## 风险提示")
    for flag in report.get("risk_flags") or []:
        lines.append(f"- {flag}")
    lines.append("")

    lines.append("## 证据索引")
    for item in report.get("evidence_index") or []:
        lines.append(
            f"- 阶段{item.get('phase')}: {item.get('phase_type')} steps={item.get('step_range')} rules={item.get('rules')}"
        )
    lines.append("")

    return "\n".join(lines)


def optional_llm_polish(markdown: str, facts: Dict[str, Any], enabled: bool) -> str:
    """可选 LLM 润色占位（默认不改写事实）。"""
    del facts
    if not enabled:
        return markdown
    # 当前版本仅保留原文，后续可注入 provider 实现并做事实一致性校验。
    return markdown


__all__ = [
    "build_analyst_report",
    "render_analyst_markdown",
    "optional_llm_polish",
]
