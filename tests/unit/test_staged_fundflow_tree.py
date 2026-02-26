"""staged_fundflow_tree 服务单元测试。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from calltrace.services.staged_fundflow_tree import (
    build_flow_tree,
    build_staged_fundflow_tree,
    load_tx_payload,
    render_staged_tree_markdown,
)

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests" / "fixtures" / "staged_tree_trace_sample.json"
EXPECTED_MD = ROOT / "tests" / "fixtures" / "staged_tree_expected_sample.md"


def _load_tx() -> dict:
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return data["result"][0]["transaction"]


def test_build_flow_tree_requires_call_stack():
    with pytest.raises(ValueError, match="callStack"):
        build_flow_tree({"transfers": []})


def test_build_staged_fundflow_tree_identifies_core_stages():
    tx = _load_tx()
    flow_tree = build_flow_tree(tx, include_static=False, prune=True)
    staged = build_staged_fundflow_tree(
        flow_tree,
        tx.get("transfers", []),
        address_meta={},
        tx_meta={
            "tx_hash": tx["transactionHash"],
            "from": tx["from"],
            "to": tx["to"],
            "miner": tx["miner"],
        },
    )

    stage_types = [s["stage_type"] for s in staged["stages"]]
    assert "Source" in stage_types
    assert "SwapCycle" in stage_types
    assert "LiquidationLike" in stage_types
    assert "TipSettlement" in stage_types
    assert "ProfitReturn" in stage_types


def test_template_label_enhancement_for_liquidation():
    tx = _load_tx()
    flow_tree = build_flow_tree(tx)
    staged = build_staged_fundflow_tree(
        flow_tree,
        tx.get("transfers", []),
        address_meta={},
        tx_meta={"tx_hash": tx["transactionHash"], "from": tx["from"], "to": tx["to"], "miner": tx["miner"]},
    )

    labels = [s["stage_label"] for s in staged["stages"]]
    assert any("清算执行" in x for x in labels)


def test_no_builder_tip_does_not_create_tip_stage():
    tx = _load_tx()
    tx["transfers"] = [t for t in tx["transfers"] if t["transferStep"] != 11]
    flow_tree = build_flow_tree(tx)

    staged = build_staged_fundflow_tree(
        flow_tree,
        tx.get("transfers", []),
        address_meta={},
        tx_meta={"tx_hash": tx["transactionHash"], "from": tx["from"], "to": tx["to"], "miner": tx["miner"]},
    )
    stage_types = [s["stage_type"] for s in staged["stages"]]
    assert "TipSettlement" not in stage_types


def test_executor_fallback_when_tx_to_missing():
    tx = _load_tx()
    tx["to"] = ""
    flow_tree = build_flow_tree(tx)
    staged = build_staged_fundflow_tree(
        flow_tree,
        tx.get("transfers", []),
        address_meta={},
        tx_meta={"tx_hash": tx["transactionHash"], "from": tx["from"], "to": "", "miner": tx["miner"]},
    )
    assert staged["executor"] == "0xf00001968c1d6196d3d0553030c7af8d1905dcbb"


def test_markdown_render_contains_asset_and_step_refs():
    tx = _load_tx()
    flow_tree = build_flow_tree(tx)
    staged = build_staged_fundflow_tree(
        flow_tree,
        tx.get("transfers", []),
        address_meta={},
        tx_meta={"tx_hash": tx["transactionHash"], "from": tx["from"], "to": tx["to"], "miner": tx["miner"]},
    )

    md = render_staged_tree_markdown(staged)
    assert "WETH" in md
    assert "USDC" in md
    assert "[#9-#11]" in md or "[#9]" in md
    assert "支付 Builder Tip" in md
    assert md == EXPECTED_MD.read_text(encoding="utf-8")


def test_render_rejects_unknown_style():
    with pytest.raises(ValueError, match="example"):
        render_staged_tree_markdown({"stages": [], "token_views": []}, style="unknown")


def test_load_tx_payload_from_input_json(tmp_path: Path):
    input_path = tmp_path / "payload.json"
    input_path.write_text(FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")

    loaded = load_tx_payload(
        "0x111122223333444455556666777788889999aaaabbbbccccddddeeeeffff0000",
        input_path,
        fetch=False,
        cache_dir=tmp_path,
    )
    assert loaded["status"] == "ok"


def test_load_tx_payload_rejects_invalid_tx_hash(tmp_path: Path):
    with pytest.raises(ValueError, match="tx_hash"):
        load_tx_payload("bad-hash", None, fetch=False, cache_dir=tmp_path)


def test_build_flow_tree_excludes_staticcall_when_disabled():
    tx = _load_tx()
    tx["callStack"]["children"].append(
        {
            "frameId": "0_static",
            "type": "STATICCALL",
            "from": tx["to"],
            "to": "0x1111111111111111111111111111111111111111",
            "transferCount": 0,
            "children": [],
        }
    )
    out = build_flow_tree(tx, include_static=False, prune=False)
    frame_ids = [c["frameId"] for c in out["root"]["children"]]
    assert "0_static" not in frame_ids
