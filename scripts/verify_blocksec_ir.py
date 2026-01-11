#!/usr/bin/env python3
"""Validate BlockSec IR building by calling BlockSec APIs and applying extra payloads."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from calltrace.services.ir_v1_blocksec import build_blocksec_ir

BASE_URL = "https://app.blocksec.com/api/v1/onchain/tx"
ENDPOINTS = {
    "trace": "trace",
    "fundflow": "fundflow",
    "balance_change": "balance-change",
    "token_info": "token-info",
    "address_label": "address-label",
    "basic_info": "basic-info",
    "gas_flame": "gas-flame",
}


def _find_trace_payload(payload: object) -> Optional[Dict[str, Any]]:
    if isinstance(payload, dict):
        if "dataMap" in payload and "mainTrace" in payload:
            return payload
        for key in ("data", "result"):
            sub = payload.get(key)
            if isinstance(sub, dict) and "dataMap" in sub and "mainTrace" in sub:
                return sub
    return None


def _unwrap_payload(payload: object) -> object:
    if isinstance(payload, dict):
        for key in ("data", "result"):
            if key in payload:
                return payload[key]
    return payload


def _post_json(url: str, payload: Dict[str, Any], headers: Dict[str, str], timeout: int) -> Any:
    data = json.dumps(payload).encode("utf-8")
    req = Request(url, data=data, headers=headers, method="POST")
    with urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
    return json.loads(raw.decode("utf-8"))


def _fetch_payloads(tx_hash: str, cookie: Optional[str], timeout: int) -> Dict[str, Any]:
    headers = {
        "accept": "application/json",
        "content-type": "application/json;charset=utf-8",
        "origin": "https://app.blocksec.com",
        "referer": f"https://app.blocksec.com/explorer/tx/eth/{tx_hash}",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
    }
    if cookie:
        headers["cookie"] = cookie

    payload = {"chainID": 1, "txnHash": tx_hash, "blocked": False}
    collected: Dict[str, Any] = {}

    for name, endpoint in ENDPOINTS.items():
        url = f"{BASE_URL}/{endpoint}"
        try:
            response = _post_json(url, payload, headers, timeout)
        except (HTTPError, URLError) as exc:
            raise RuntimeError(f"Failed to fetch {endpoint}: {exc}") from exc

        if name == "trace":
            trace_payload = _find_trace_payload(response)
            if trace_payload is None:
                raise RuntimeError("Trace response missing dataMap/mainTrace")
            collected["trace_data"] = trace_payload
        else:
            collected[name] = _unwrap_payload(response)

    return collected


def _ordered_by_keys(data: Dict[str, Any], key_order: List[str]) -> Dict[str, Any]:
    ordered: Dict[str, Any] = {}
    for key in key_order:
        if key in data:
            ordered[key] = data[key]
    for key in data:
        if key not in ordered:
            ordered[key] = data[key]
    return ordered


def _order_ir_value(value: Any) -> Any:
    if isinstance(value, dict):
        return _order_ir_dict(value)
    if isinstance(value, list):
        return [_order_ir_value(item) for item in value]
    return value


def _order_ir_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    processed = {key: _order_ir_value(value) for key, value in data.items()}

    top_level_order = ["tx_hash", "pattern", "baseTokenAmountIn", "baseTokenAmountOut", "rootTrace", "children"]
    root_trace_order = ["type", "swap", "transfer", "wethWrapOrUnwarp", "callback", "encoded"]
    swap_order = ["swapIntent", "executionArgs"]
    swap_intent_order = [
        "poolId",
        "protocolId",
        "tokenIn",
        "tokenInDecimals",
        "tokenOut",
        "tokenOutDecimals",
        "amountIn",
        "amountInBig",
        "amountInEncoded",
        "amountOut",
        "amountOutBig",
        "amountOutEncoded",
    ]
    exec_args_order = [
        "amount",
        "isAmountIn",
        "zeroForOne",
        "recipientIsBot",
        "recipient",
        "recipientType",
        "tokenInIsWETH",
        "tokenOutIsWETH",
    ]
    transfer_order = ["tokenId", "to", "amount"]

    if "rootTrace" in processed and "children" in processed:
        return _ordered_by_keys(processed, top_level_order)

    if "swapIntent" in processed or "executionArgs" in processed:
        ordered = _ordered_by_keys(processed, swap_order)
        if "swapIntent" in ordered and isinstance(ordered.get("swapIntent"), dict):
            ordered["swapIntent"] = _ordered_by_keys(ordered["swapIntent"], swap_intent_order)
        if "executionArgs" in ordered and isinstance(ordered.get("executionArgs"), dict):
            ordered["executionArgs"] = _ordered_by_keys(ordered["executionArgs"], exec_args_order)
        return ordered

    if "poolId" in processed and "protocolId" in processed and ("tokenIn" in processed or "tokenOut" in processed):
        return _ordered_by_keys(processed, swap_intent_order)

    if "type" in processed and ("swap" in processed or "transfer" in processed):
        return _ordered_by_keys(processed, root_trace_order)

    if set(transfer_order).issubset(processed.keys()):
        return _ordered_by_keys(processed, transfer_order)

    return processed


def _compare_ir(actual: Any, expected: Any, path: str, issues: List[str]) -> None:
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            issues.append(f"{path} expected dict")
            return
        if list(actual.keys()) != list(expected.keys()):
            issues.append(f"{path} key order mismatch")
        for key, exp_value in expected.items():
            _compare_ir(actual.get(key), exp_value, f"{path}.{key}" if path else key, issues)
        return
    if isinstance(expected, list):
        if not isinstance(actual, list):
            issues.append(f"{path} expected list")
            return
        if len(actual) != len(expected):
            issues.append(f"{path} length mismatch")
            return
        for idx, exp_value in enumerate(expected):
            _compare_ir(actual[idx], exp_value, f"{path}[{idx}]", issues)
        return
    if isinstance(expected, float):
        if not isinstance(actual, (int, float)):
            issues.append(f"{path} expected number")
            return
        if abs(actual - expected) > 1e-12:
            issues.append(f"{path} float mismatch")
        return
    if actual != expected:
        issues.append(f"{path} mismatch")


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text())


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate BlockSec IR with extra payloads")
    parser.add_argument("--tx-hash", required=True, help="Transaction hash")
    parser.add_argument("--cookie", help="Cookie header value")
    parser.add_argument("--cookie-file", help="Path to file containing Cookie header")
    parser.add_argument("--expected", help="Path to expected IR JSON")
    parser.add_argument("--output", help="Path to write generated IR JSON")
    parser.add_argument("--dump-dir", help="Directory to dump raw payloads")
    parser.add_argument("--timeout", type=int, default=30, help="HTTP timeout seconds")
    args = parser.parse_args()

    cookie = args.cookie
    if args.cookie_file:
        cookie = Path(args.cookie_file).read_text().strip()

    payloads = _fetch_payloads(args.tx_hash, cookie, args.timeout)
    trace_data = payloads.get("trace_data")
    extra = {key: value for key, value in payloads.items() if key != "trace_data"}

    if args.dump_dir:
        dump_dir = Path(args.dump_dir)
        dump_dir.mkdir(parents=True, exist_ok=True)
        for key, value in payloads.items():
            (dump_dir / f"{key}.json").write_text(json.dumps(value, indent=2))

    ir = build_blocksec_ir(trace_data, args.tx_hash, extra)
    ordered_ir = _order_ir_dict(ir)

    if args.output:
        Path(args.output).write_text(json.dumps(ordered_ir, indent=2))
    else:
        print(json.dumps(ordered_ir, indent=2))

    if args.expected:
        expected = _order_ir_dict(_load_json(Path(args.expected)))
        issues: List[str] = []
        _compare_ir(ordered_ir, expected, "", issues)
        if issues:
            print("\nValidation failed:")
            for issue in issues[:20]:
                print(f"- {issue}")
            return 1
        print("\nValidation passed.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
