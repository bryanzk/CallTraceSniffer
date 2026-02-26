"""staged_fundflow_tree CLI 集成测试。"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "parse" / "staged_fundflow_tree.py"
FIXTURE = ROOT / "tests" / "fixtures" / "staged_tree_trace_sample.json"


def test_cli_generates_json_and_markdown(tmp_path: Path):
    output_json = tmp_path / "out.json"
    output_md = tmp_path / "out.md"

    cmd = [
        sys.executable,
        str(SCRIPT),
        "--tx-hash",
        "0x111122223333444455556666777788889999aaaabbbbccccddddeeeeffff0000",
        "--input-json",
        str(FIXTURE),
        "--output-json",
        str(output_json),
        "--output-md",
        str(output_md),
    ]
    subprocess.run(cmd, check=True, cwd=ROOT)

    assert output_json.exists()
    assert output_md.exists()

    staged = json.loads(output_json.read_text(encoding="utf-8"))
    stage_types = [s["stage_type"] for s in staged["stages"]]
    assert "TipSettlement" in stage_types
    assert "ProfitReturn" in stage_types

    md = output_md.read_text(encoding="utf-8")
    assert "支付 Builder Tip" in md
    assert "利润回流" in md
