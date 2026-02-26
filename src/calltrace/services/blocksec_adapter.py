"""BlockSec parser adapter.

Loads the standalone `blocksec-parser` package and provides stable adapter
functions for the legacy CallTraceSniffer service layer.
"""

from __future__ import annotations

from functools import lru_cache
from importlib import import_module
from pathlib import Path
import sys
from types import ModuleType
from typing import Any


def _candidate_local_package_src() -> Path:
    # .../CallTraceSniffer/src/calltrace/services/blocksec_adapter.py
    # -> .../CallTraceSniffer
    repo_root = Path(__file__).resolve().parents[3]
    return repo_root.parent / "blocksec-parser" / "src"


@lru_cache(maxsize=1)
def _load_blocksec_module(module_name: str) -> ModuleType:
    try:
        return import_module(module_name)
    except ModuleNotFoundError:
        candidate = _candidate_local_package_src()
        if candidate.exists() and str(candidate) not in sys.path:
            sys.path.insert(0, str(candidate))
        return import_module(module_name)


def get_playwright_extractor_class() -> type:
    mod = _load_blocksec_module("blocksec_parser.playwright_extractor")
    return mod.PlaywrightBlockSecExtractor


def parse_tx(tx_hash: str, strategy: str = "auto") -> Any:
    mod = _load_blocksec_module("blocksec_parser")
    return mod.parse_tx(tx_hash, strategy=strategy)


def parse_simulation_url_result(sim_url: str, strategy: str = "auto") -> Any:
    mod = _load_blocksec_module("blocksec_parser")
    return mod.parse_simulation_url(sim_url, strategy=strategy)


def parse_simulation_url_tuple(sim_url: str) -> tuple[str, str]:
    mod = _load_blocksec_module("blocksec_parser.validators")
    return mod.parse_simulation_url(sim_url)


def sanitize_payload(raw_payload: dict[str, Any]) -> dict[str, Any]:
    mod = _load_blocksec_module("blocksec_parser")
    return mod.sanitize_payload(raw_payload)


def fetch_payload_via_api(tx_hash: str, timeout_sec: int = 45) -> dict[str, Any]:
    mod = _load_blocksec_module("blocksec_parser.api_fallback_client")
    return mod.fetch_blocksec_payload_via_api(tx_hash, timeout_sec=timeout_sec)
