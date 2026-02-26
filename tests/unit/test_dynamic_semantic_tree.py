"""动态语义切分执行结构树测试。"""

from __future__ import annotations

import json
from pathlib import Path

from calltrace.services.staged_fundflow_tree import (
    build_dynamic_semantic_tree,
    render_dynamic_semantic_markdown,
)

ROOT = Path(__file__).resolve().parents[2]
CASE_92E8 = ROOT / "tests" / "fixtures" / "dynamic_semantic_case_92e8.json"
CASE_ALT = ROOT / "tests" / "fixtures" / "dynamic_semantic_case_alt.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_dynamic_semantic_tree_detects_adaptive_phases_for_92e8():
    payload = _load(CASE_92E8)
    out = build_dynamic_semantic_tree(payload, "0x92e8b6cf1367b5db3810186be30a3148e49283fe33f980919905f0433b1738de")

    phase_types = [x["phase_type"] for x in out["phases"]]
    assert "Borrow" in phase_types
    assert "Repay" in phase_types
    assert "Liquidation" in phase_types
    assert "Swap" in phase_types
    assert "Tip" in phase_types
    assert "Profit" in phase_types


def test_dynamic_semantic_tree_is_not_fixed_template_count():
    p1 = _load(CASE_92E8)
    p2 = _load(CASE_ALT)
    o1 = build_dynamic_semantic_tree(p1, "0x92e8b6cf1367b5db3810186be30a3148e49283fe33f980919905f0433b1738de")
    o2 = build_dynamic_semantic_tree(p2, "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
    assert len(o1["phases"]) != len(o2["phases"])


def test_dynamic_phase_has_rules_confidence_and_inferred():
    payload = _load(CASE_92E8)
    out = build_dynamic_semantic_tree(payload, "0x92e8b6cf1367b5db3810186be30a3148e49283fe33f980919905f0433b1738de")
    for phase in out["phases"]:
        assert isinstance(phase["rules_matched"], list)
        assert 0 <= phase["confidence"] <= 1
        assert isinstance(phase["inferred"], bool)


def test_low_evidence_can_fallback_to_other_in_strict_mode():
    payload = _load(CASE_ALT)
    out = build_dynamic_semantic_tree(payload, "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", strict=True)
    assert any(p["phase_type"] == "Other" for p in out["phases"])


def test_render_dynamic_markdown_contains_tree_and_confidence():
    payload = _load(CASE_92E8)
    out = build_dynamic_semantic_tree(payload, "0x92e8b6cf1367b5db3810186be30a3148e49283fe33f980919905f0433b1738de")
    md = render_dynamic_semantic_markdown(out)
    assert "Tx 0x92e8" in md
    assert "CALL" in md
    assert "confidence=" in md
    assert "[阶段" in md


def test_dynamic_semantic_tree_requires_callstack():
    payload = {
        "status": "ok",
        "result": [{"transaction": {"transactionHash": "0x" + "1" * 64, "transfers": []}}],
    }
    try:
        build_dynamic_semantic_tree(payload, "0x" + "1" * 64)
        assert False, "应抛出异常"
    except ValueError as exc:
        assert "callStack" in str(exc)


def test_dynamic_markdown_handles_empty_phases():
    tree = {
        "tx_hash": "0x" + "1" * 64,
        "root_actor": "EOA / Liquidator 0xabc",
        "root_call_target": "CALL 0xdef",
        "phases": [],
        "summary": {"phase_count": 0, "transfer_count": 0},
    }
    md = render_dynamic_semantic_markdown(tree)
    assert "Tx 0x1111" in md
    assert "CALL 0xdef" in md
