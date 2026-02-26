#!/usr/bin/env python3
"""最小 FastAPI 封装：POST tx_hash 生成 semantic report。"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Optional

try:
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel, Field
except Exception as exc:  # pragma: no cover
    raise SystemExit(
        "fastapi/pydantic 未安装。请先执行: python3 -m pip install fastapi uvicorn pydantic"
    ) from exc

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from calltrace.services.semantic_report import (  # noqa: E402
    build_analyst_report,
    optional_llm_polish,
    render_analyst_markdown,
)
from calltrace.services.staged_fundflow_tree import (  # noqa: E402
    build_dynamic_semantic_tree,
    load_tx_payload,
)


class SemanticReportRequest(BaseModel):
    tx_hash: str = Field(..., description="交易哈希")
    input_json: Optional[str] = Field(default=None, description="本地 analyseTransaction JSON 路径")
    fetch: bool = Field(default=False, description="缺失本地文件时是否联网抓取")
    network_only: bool = Field(default=True, description="强制联网直读（忽略本地文件与缓存）")
    strict: bool = Field(default=True, description="严格模式")
    report_style: str = Field(default="default", description="报告风格")
    report_llm: bool = Field(default=False, description="是否启用 LLM 润色")
    report_llm_provider: Optional[str] = Field(default=None, description="LLM provider 占位参数")


class SemanticReportResponse(BaseModel):
    success: bool
    tx_hash: str
    dynamic_semantic_tree: dict[str, Any]
    report: dict[str, Any]
    report_markdown: str


app = FastAPI(title="Semantic Report API", version="1.0.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/semantic-report", response_model=SemanticReportResponse)
def semantic_report(req: SemanticReportRequest) -> SemanticReportResponse:
    tx_hash = (req.tx_hash or "").strip().lower()
    if not tx_hash:
        raise HTTPException(status_code=400, detail="tx_hash 不能为空")

    input_path = None
    if req.network_only and req.input_json:
        raise HTTPException(status_code=400, detail="network_only=true 时不允许 input_json")
    if req.input_json:
        input_path = Path(req.input_json)
        if not input_path.exists():
            raise HTTPException(status_code=400, detail=f"input_json 不存在: {req.input_json}")

    try:
        payload = load_tx_payload(
            tx_hash=tx_hash,
            input_json=input_path,
            fetch=(True if req.network_only else req.fetch),
            cache_dir=ROOT / "outputs",
            read_cache=(False if req.network_only else True),
            write_cache=(False if req.network_only else True),
        )
        tree = build_dynamic_semantic_tree(payload, tx_hash=tx_hash, strict=req.strict)
        report = build_analyst_report(tree, style=req.report_style)
        markdown = render_analyst_markdown(report)
        markdown = optional_llm_polish(markdown, facts=tree, enabled=req.report_llm)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=f"生成报告失败: {exc}") from exc

    return SemanticReportResponse(
        success=True,
        tx_hash=tx_hash,
        dynamic_semantic_tree=tree,
        report=report,
        report_markdown=markdown,
    )


if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    uvicorn.run("scripts.api.semantic_report_fastapi:app", host="0.0.0.0", port=8000, reload=False)
