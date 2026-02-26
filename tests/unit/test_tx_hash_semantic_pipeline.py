import os
from pathlib import Path
import sys
import types

import pytest

import calltrace.services.tx_hash_semantic_pipeline as pipeline
from calltrace.services.tx_hash_semantic_pipeline import (
    build_artifact_paths,
    build_eigenphi_json_url,
    build_eigenphi_svg_url,
    choose_multimodal_image_path,
    load_env_from_dotenv_if_missing,
    normalize_tx_hash,
    sanitize_blocksec_payload,
)


def test_normalize_tx_hash_accepts_uppercase_and_rejects_invalid():
    tx_hash = "0x" + ("A" * 64)
    assert normalize_tx_hash(tx_hash) == "0x" + ("a" * 64)

    with pytest.raises(ValueError):
        normalize_tx_hash("0x1234")

    with pytest.raises(ValueError):
        normalize_tx_hash("xyz")


def test_build_eigenphi_urls():
    tx_hash = "0x" + ("b" * 64)
    assert build_eigenphi_json_url(tx_hash).endswith(f"tx={tx_hash}")
    assert build_eigenphi_svg_url(tx_hash).endswith(f"tx={tx_hash}&rankdir=LR")


def test_build_artifact_paths(tmp_path: Path):
    tx_hash = "0x" + ("1" * 64)
    artifacts = build_artifact_paths(tmp_path, tx_hash)

    expected_dir = tmp_path / tx_hash
    assert artifacts.base_dir == expected_dir
    assert artifacts.eigenphi_json == expected_dir / f"{tx_hash}_eigenphi.json"
    assert artifacts.blocksec_json == expected_dir / f"{tx_hash}_blocksec.json"
    assert artifacts.eigenphi_svg == expected_dir / f"{tx_hash}.svg"
    assert artifacts.selector_signatures_json == expected_dir / "selector_signatures_4byte.json"
    assert artifacts.semantic_markdown == expected_dir / "semantic_tree_openai_shell_mvp.md"


def test_sanitize_blocksec_payload_filters_meta_keys():
    raw = {
        "success": True,
        "tx_hash": "0x" + ("2" * 64),
        "trace_data": {"mainTrace": [], "dataMap": {}},
        "fundflow": [{"id": 1}],
    }

    cleaned = sanitize_blocksec_payload(raw)
    assert "success" not in cleaned
    assert "tx_hash" not in cleaned
    assert cleaned["trace_data"]["mainTrace"] == []
    assert cleaned["fundflow"] == [{"id": 1}]


def test_sanitize_blocksec_payload_requires_trace_data():
    with pytest.raises(ValueError):
        sanitize_blocksec_payload({"success": True, "fundflow": []})

    with pytest.raises(ValueError):
        sanitize_blocksec_payload({"success": False, "error": "bad"})


def test_choose_multimodal_image_path_prefers_raster_image(tmp_path: Path):
    svg = tmp_path / "a.svg"
    svg.write_text("<svg></svg>")
    png = tmp_path / "b.png"
    png.write_bytes(b"\x89PNG\r\n\x1a\n")

    assert choose_multimodal_image_path(svg) is None
    assert choose_multimodal_image_path(png) == str(png)


def test_load_env_from_dotenv_if_missing_sets_only_missing_keys(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    env_path = tmp_path / ".env"
    env_path.write_text(
        "OPENAI_API_KEY=sk-test-key\n"
        "SOME_OTHER=foo\n",
        encoding="utf-8",
    )

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("SOME_OTHER", "bar")

    load_env_from_dotenv_if_missing(env_path)

    assert "OPENAI_API_KEY" in os.environ
    assert os.environ["OPENAI_API_KEY"] == "sk-test-key"
    assert os.environ["SOME_OTHER"] == "bar"


def test_extract_blocksec_payload_fallbacks_to_api(monkeypatch: pytest.MonkeyPatch):
    class FakeExtractor:
        async def extract_blocksec_data(self, tx_hash: str):
            return {"success": False, "error": "extractor_failed"}

    fake_module = types.ModuleType("calltrace.services.extractor")
    fake_module.BlockSecExtractor = FakeExtractor
    monkeypatch.setitem(sys.modules, "calltrace.services.extractor", fake_module)

    monkeypatch.setattr(
        pipeline,
        "fetch_blocksec_payload_via_api",
        lambda tx_hash, timeout_sec=45: {"trace_data": {"dataMap": {}, "mainTrace": []}},
    )

    payload = pipeline.extract_blocksec_payload("0x" + ("3" * 64))
    assert "trace_data" in payload
