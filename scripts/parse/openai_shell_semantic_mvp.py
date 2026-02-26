#!/usr/bin/env python3
"""使用 OpenAI Responses + Shell 工具生成业务语义结构树（MVP）。"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from calltrace.services.openai_shell_semantic_mvp import (  # noqa: E402
    DEFAULT_ALLOWED_COMMAND_PREFIXES,
    build_semantic_prompt,
    generate_semantic_tree_with_shell,
)


SHELL_FRIENDLY_MODELS: tuple[str, ...] = (
    "gpt-5.1",
    "gpt-5.2",
    "gpt-5.1-codex",
    "gpt-5.2-codex",
)


def main() -> int:
    parser = argparse.ArgumentParser(description="OpenAI Shell MVP 语义树生成器")
    parser.add_argument(
        "--eigenphi-json",
        "--tx-json",
        dest="eigenphi_json",
        default="local/sample0x8c/0x8c_eigenphi.json",
        help="EigenPhi 交易 JSON 路径（兼容旧参数 --tx-json）",
    )
    parser.add_argument(
        "--blocksec-json",
        default="local/sample0x8c/0x8c_blocksec.json",
        help="BlockSec 交易 JSON 路径",
    )
    parser.add_argument(
        "--rule-json",
        default="local/sample0x8c/phase_rule.json",
        help="phase rule JSON 路径",
    )
    parser.add_argument(
        "--reference-image",
        default="local/sample0x8c/8c.png",
        help="参考图片路径（例如 8c.png）",
    )
    parser.add_argument(
        "--output-md",
        default="local/sample0x8c/semantic_tree_openai_shell_mvp.md",
        help="输出 Markdown 路径",
    )
    parser.add_argument(
        "--model",
        default="gpt-5.2",
        help="Responses API 模型名（shell 工具建议使用 gpt-5.1 / gpt-5.2 / gpt-5.1-codex / gpt-5.2-codex）",
    )
    parser.add_argument("--max-turns", type=int, default=16, help="最大 shell 推理轮数")
    parser.add_argument(
        "--workdir",
        default=str(ROOT),
        help="本地 shell 命令执行目录",
    )
    args = parser.parse_args()

    eigenphi_path = (
        (ROOT / args.eigenphi_json).resolve()
        if not Path(args.eigenphi_json).is_absolute()
        else Path(args.eigenphi_json)
    )
    blocksec_path = (
        (ROOT / args.blocksec_json).resolve()
        if not Path(args.blocksec_json).is_absolute()
        else Path(args.blocksec_json)
    )
    rule_path = (ROOT / args.rule_json).resolve() if not Path(args.rule_json).is_absolute() else Path(args.rule_json)
    image_path = (
        (ROOT / args.reference_image).resolve()
        if not Path(args.reference_image).is_absolute()
        else Path(args.reference_image)
    )
    out_path = (ROOT / args.output_md).resolve() if not Path(args.output_md).is_absolute() else Path(args.output_md)

    if not eigenphi_path.exists():
        raise FileNotFoundError(f"eigenphi json not found: {eigenphi_path}")
    if not blocksec_path.exists():
        raise FileNotFoundError(f"blocksec json not found: {blocksec_path}")
    if not rule_path.exists():
        raise FileNotFoundError(f"rule json not found: {rule_path}")
    if not image_path.exists():
        raise FileNotFoundError(f"reference image not found: {image_path}")

    prompt = build_semantic_prompt(
        eigenphi_json_path=str(eigenphi_path),
        blocksec_json_path=str(blocksec_path),
        rule_json_path=str(rule_path),
        reference_image_path=str(image_path),
        output_markdown_path=str(out_path),
    )

    try:
        from openai import OpenAI
    except Exception as exc:
        raise RuntimeError(
            "需要先安装 openai 包。建议使用项目虚拟环境："
            ".run_venv/bin/python -m pip install openai"
        ) from exc

    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("缺少 OPENAI_API_KEY。请先执行: export OPENAI_API_KEY=你的key")

    client = OpenAI()
    try:
        text = generate_semantic_tree_with_shell(
            client=client,
            model=args.model,
            prompt=prompt,
            reference_image_path=str(image_path),
            cwd=args.workdir,
            max_turns=args.max_turns,
            allowed_prefixes=DEFAULT_ALLOWED_COMMAND_PREFIXES,
        )
    except Exception as exc:
        # 在不绑定 SDK 私有类型的前提下，识别典型的模型/工具不兼容错误并给出可执行建议。
        msg = str(exc)
        if "Tool 'shell' is not supported" in msg or '"tools"' in msg and "not supported" in msg:
            suggested = ", ".join(SHELL_FRIENDLY_MODELS)
            raise RuntimeError(
                f"当前模型 `{args.model}` 不支持 shell 工具。请改用: {suggested}"
            ) from exc
        raise

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text, encoding="utf-8")

    print(str(out_path))
    print(f"chars={len(text)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
