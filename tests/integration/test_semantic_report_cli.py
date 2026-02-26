"""分析师报告 CLI 集成测试。"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "parse" / "staged_fundflow_tree.py"
FIXTURE = ROOT / "tests" / "fixtures" / "dynamic_semantic_case_92e8.json"


def test_cli_generates_report_outputs(tmp_path: Path):
    report_md = tmp_path / "report.md"

    cmd = [
        sys.executable,
        str(SCRIPT),
        "--tx-hash",
        "0x92e8b6cf1367b5db3810186be30a3148e49283fe33f980919905f0433b1738de",
        "--input-json",
        str(FIXTURE),
        "--dynamic-semantic",
        "--report",
        "--report-output-md",
        str(report_md),
        "--strict",
    ]
    subprocess.run(cmd, check=True, cwd=ROOT)

    assert report_md.exists()
    text = report_md.read_text(encoding="utf-8")
    assert "执行摘要" in text
    assert "阶段" in text


def test_cli_report_llm_flag_does_not_break(tmp_path: Path):
    report_md = tmp_path / "report_llm.md"

    cmd = [
        sys.executable,
        str(SCRIPT),
        "--tx-hash",
        "0x92e8b6cf1367b5db3810186be30a3148e49283fe33f980919905f0433b1738de",
        "--input-json",
        str(FIXTURE),
        "--dynamic-semantic",
        "--report",
        "--report-llm",
        "--report-llm-provider",
        "mock",
        "--report-output-md",
        str(report_md),
    ]
    subprocess.run(cmd, check=True, cwd=ROOT)

    assert report_md.exists()
