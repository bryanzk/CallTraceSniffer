"""分析师报告生成单元测试。"""

from __future__ import annotations

import json
from pathlib import Path

from calltrace.services.semantic_report import (
    build_analyst_report,
    optional_llm_polish,
    render_analyst_markdown,
)
from calltrace.services.staged_fundflow_tree import build_dynamic_semantic_tree

ROOT = Path(__file__).resolve().parents[2]
DYNAMIC_FIXTURE = ROOT / "tests" / "fixtures" / "dynamic_semantic_case_92e8.json"
EXPECTED_MD = ROOT / "tests" / "fixtures" / "semantic_report_expected_92e8.md"


def _build_tree() -> dict:
    payload = json.loads(DYNAMIC_FIXTURE.read_text(encoding="utf-8"))
    return build_dynamic_semantic_tree(payload, "0x92e8b6cf1367b5db3810186be30a3148e49283fe33f980919905f0433b1738de")


def test_build_analyst_report_basic_structure():
    tree = _build_tree()
    report = build_analyst_report(tree)

    assert report["tx_hash"].startswith("0x92e8")
    assert "executive_summary" in report
    assert isinstance(report["phase_narratives"], list)
    assert len(report["phase_narratives"]) == len(tree["phases"])


def test_report_keeps_key_facts_steps_and_amounts():
    tree = _build_tree()
    report = build_analyst_report(tree)
    md = render_analyst_markdown(report)

    assert "#23" in md
    assert "4.043857" in md
    assert "0xdadb" in md.lower()


def test_report_marks_inferred_phase():
    tree = _build_tree()
    report = build_analyst_report(tree)
    inferred_texts = [p["confidence_text"] for p in report["phase_narratives"]]
    assert any("推断" in x for x in inferred_texts)


def test_optional_llm_polish_default_keeps_text():
    source = "hello world"
    out = optional_llm_polish(source, {"tx_hash": "0x1"}, enabled=False)
    assert out == source


def test_render_analyst_markdown_snapshot_like():
    tree = _build_tree()
    report = build_analyst_report(tree)
    md = render_analyst_markdown(report)

    assert "执行摘要" in md
    assert "风险提示" in md
    # 快照文件可由实现后固化
    if EXPECTED_MD.exists():
        assert md == EXPECTED_MD.read_text(encoding="utf-8")
