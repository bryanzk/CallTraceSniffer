# 资金流执行结构树脚本单元测试
"""Tests for scripts/parse/flow_tree_from_trace_json.py"""

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
FIXTURE_DIR = ROOT / "tests" / "fixtures"
SCRIPT_PATH = ROOT / "scripts" / "parse" / "flow_tree_from_trace_json.py"


def _load_flow_tree_module():
    spec = importlib.util.spec_from_file_location(
        "flow_tree_from_trace_json",
        SCRIPT_PATH,
        submodule_search_locations=[str(SCRIPT_PATH.parent)],
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod._get_transaction, mod._group_transfers_by_frame_id, mod.build_flow_tree


def test_get_transaction_requires_result():
    _get_transaction, _, _ = _load_flow_tree_module()
    with pytest.raises(ValueError, match="result"):
        _get_transaction({})
    with pytest.raises(ValueError, match="result"):
        _get_transaction({"result": []})


def test_get_transaction_requires_transaction():
    _get_transaction, _, _ = _load_flow_tree_module()
    with pytest.raises(ValueError, match="transaction"):
        _get_transaction({"result": [{}]})


def test_build_flow_tree_requires_call_stack():
    _, _, build_flow_tree = _load_flow_tree_module()
    with pytest.raises(ValueError, match="callStack"):
        build_flow_tree({"transfers": []})


def test_build_flow_tree_from_fixture():
    _, _, build_flow_tree = _load_flow_tree_module()
    path = FIXTURE_DIR / "flow_tree_trace_sample.json"
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    tx = data["result"][0]["transaction"]
    out = build_flow_tree(tx)

    assert out["tx_hash"] == "0xa5c9243ad9599426d7a0a02ae6a7603bf7914f17aeba4cfd4e2aedd2f25bebc3"
    assert "0xcafecd3587d7b627620022cffee76d404c2195c3" in out["from"]
    assert "0xf00001968c1d6196d3d0553030c7af8d1905dcbb" in out["to"]

    root = out["root"]
    assert root["frameId"] == "0"
    assert root["transferCount"] == 14
    assert root["type"] == "CALL"

    child_0_2 = next((c for c in root["children"] if c.get("frameId") == "0_2"), None)
    assert child_0_2 is not None
    assert child_0_2["transferCount"] == 10
    assert "flashLoan" in (child_0_2.get("methodNames") or [])


def test_build_flow_tree_attaches_transfers_by_frame_id():
    _, _, build_flow_tree = _load_flow_tree_module()
    path = FIXTURE_DIR / "flow_tree_trace_sample.json"
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    tx = data["result"][0]["transaction"]
    out = build_flow_tree(tx)

    # 叶子 0_2_0_0 应挂载 frameId 为 0_2_0_0 的 1 笔转账
    root = out["root"]
    c02 = next((c for c in root["children"] if c.get("frameId") == "0_2"), None)
    assert c02 is not None
    c020 = next((c for c in c02["children"] if c.get("frameId") == "0_2_0"), None)
    assert c020 is not None
    c0200 = next((c for c in c020["children"] if c.get("frameId") == "0_2_0_0"), None)
    assert c0200 is not None
    assert len(c0200["transfers"]) == 1
    assert c0200["transfers"][0]["transferStep"] == 0
    assert c0200["transfers"][0]["token"] == "WETH"


def test_build_flow_tree_prune_keeps_root_and_nodes_with_transfers():
    _, _, build_flow_tree = _load_flow_tree_module()
    path = FIXTURE_DIR / "flow_tree_trace_sample.json"
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    tx = data["result"][0]["transaction"]
    out = build_flow_tree(tx, prune=True)

    root = out["root"]
    assert root["frameId"] == "0"
    # 剪枝后应仍保留有后代的路径（0_2 -> 0_2_0 -> 0_2_0_0）
    assert len(root["children"]) >= 1
    child_0_2 = next((c for c in root["children"] if c.get("frameId") == "0_2"), None)
    assert child_0_2 is not None
