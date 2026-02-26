"""动态语义 CLI 集成测试。"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "parse" / "staged_fundflow_tree.py"
FIXTURE = ROOT / "tests" / "fixtures" / "dynamic_semantic_case_92e8.json"


def test_cli_generates_dynamic_semantic_outputs(tmp_path: Path):
    out_json = tmp_path / "semantic.json"
    out_md = tmp_path / "semantic.md"

    cmd = [
        sys.executable,
        str(SCRIPT),
        "--tx-hash",
        "0x92e8b6cf1367b5db3810186be30a3148e49283fe33f980919905f0433b1738de",
        "--input-json",
        str(FIXTURE),
        "--dynamic-semantic",
        "--semantic-output-json",
        str(out_json),
        "--semantic-output-md",
        str(out_md),
        "--strict",
    ]
    subprocess.run(cmd, check=True, cwd=ROOT)

    assert out_json.exists()
    assert out_md.exists()

    payload = json.loads(out_json.read_text(encoding="utf-8"))
    assert "phases" in payload
    assert all("confidence" in p for p in payload["phases"])

    text = out_md.read_text(encoding="utf-8")
    assert "CALL" in text
    assert "阶段" in text
