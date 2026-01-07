#!/usr/bin/env python3
"""Convert IR JSON to Mermaid DAG with typed table nodes."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict

from calltrace.services.mermaid_dag import build_mermaid_dag


def ir_to_mermaid(ir: Dict[str, Any]) -> str:
    return build_mermaid_dag(ir)


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert IR JSON to Mermaid DAG.")
    parser.add_argument("input", help="Path to IR JSON file (output of IR V1). Use - for stdin.")
    args = parser.parse_args()

    if args.input == "-":
        data = json.load(sys.stdin)
    else:
        with open(args.input, "r", encoding="utf-8") as handle:
            data = json.load(handle)

    mermaid = ir_to_mermaid(data)
    sys.stdout.write(mermaid)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
