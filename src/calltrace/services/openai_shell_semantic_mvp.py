"""OpenAI Responses + Shell 的语义树生成 MVP。"""

from __future__ import annotations

import base64
from dataclasses import dataclass
from pathlib import Path
import shlex
import subprocess
from typing import Any, Iterable, Sequence


DEFAULT_ALLOWED_COMMAND_PREFIXES: tuple[str, ...] = (
    "python3",
    "python",
    "jq",
    "rg",
    "ls",
    "cat",
    "sed",
    "head",
    "tail",
    "wc",
)

# MVP 阶段只允许单条命令，避免注入和复杂 shell 语法风险。
DISALLOWED_SNIPPETS: tuple[str, ...] = ("&&", "||", ";", "|", ">", "<", "`", "$(")
DEFAULT_SHELL_OUTPUT_CHAR_LIMIT = 4000
HARD_MAX_SHELL_OUTPUT_CHAR_LIMIT = 12000


@dataclass(frozen=True)
class ShellCall:
    call_id: str
    commands: tuple[str, ...]
    max_output_length: int | None = None
    timeout_ms: int | None = None


@dataclass(frozen=True)
class ShellExecutionResult:
    command: str
    returncode: int
    stdout: str
    stderr: str


def _get_field(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def build_semantic_prompt(
    eigenphi_json_path: str,
    blocksec_json_path: str,
    rule_json_path: str,
    reference_image_path: str,
    output_markdown_path: str,
) -> str:
    """构建交给模型的任务描述。"""
    return (
        "你是链上业务语义分析助手。\\n"
        "目标：基于交易 JSON 与 phase rule，生成简体中文业务语义结构树。\\n"
        "必须联合使用 EigenPhi、BlockSec 与参考图片三类输入，不得只依赖单一来源。\\n"
        "必须先用 shell 工具读取/统计数据，再输出最终 Markdown。\\n"
        "执行 shell 命令时，只能使用单条命令，禁止管道/重定向/&&/||/;。\\n"
        "读取大文件时必须用 jq 精准字段或 head/tail 限量读取，不得输出整份 JSON。\\n"
        "若某条命令被策略拒绝，必须改写为更简单的单命令重试，不得直接放弃。\\n"
        "输出要求：\\n"
        "1. 标题为 TX Root。\\n"
        "2. 分阶段描述（Phase 0..N），每阶段包含核心动作与资产路径。\\n"
        "3. 必须显式体现跨数据源一致性（EigenPhi 转账轨迹 + BlockSec trace 结构 + 图片线索）。\\n"
        "4. 风格接近本地 sample 的业务树，不要输出代码块。\\n"
        "5. 最终只输出 Markdown 文本，不要附加解释。\\n\\n"
        f"输入交易文件（EigenPhi）: {eigenphi_json_path}\\n"
        f"输入交易文件（BlockSec）: {blocksec_json_path}\\n"
        f"规则文件: {rule_json_path}\\n"
        f"参考图片: {reference_image_path}\\n"
        f"目标输出文件: {output_markdown_path}\\n"
    )


def _to_image_data_url(reference_image_path: str) -> str:
    path = Path(reference_image_path)
    raw = path.read_bytes()

    suffix = path.suffix.lower()
    if suffix == ".png":
        mime = "image/png"
    elif suffix in {".jpg", ".jpeg"}:
        mime = "image/jpeg"
    elif suffix == ".webp":
        mime = "image/webp"
    else:
        mime = "application/octet-stream"

    encoded = base64.b64encode(raw).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def build_initial_input(
    prompt: str,
    reference_image_path: str | None = None,
    reference_image_file_id: str | None = None,
) -> Any:
    """构建 Responses API 初始输入；有图时走多模态 message。"""
    if not reference_image_path and not reference_image_file_id:
        return prompt

    image_item: dict[str, Any] = {"type": "input_image", "detail": "high"}
    if reference_image_file_id:
        image_item["file_id"] = reference_image_file_id
    else:
        data_url = _to_image_data_url(reference_image_path or "")
        image_item["image_url"] = data_url

    return [
        {
            "role": "user",
            "content": [
                {"type": "input_text", "text": prompt},
                image_item,
            ],
        }
    ]


def upload_reference_image_file(client: Any, reference_image_path: str) -> str:
    """上传参考图片并返回 file_id，避免把大图 base64 直接塞进上下文。"""
    with Path(reference_image_path).open("rb") as fp:
        fobj = client.files.create(
            file=fp,
            purpose="user_data",
        )
    file_id = _get_field(fobj, "id", "")
    if not file_id:
        raise RuntimeError("参考图片上传成功但未返回 file_id")
    return str(file_id)


def _truncate_text(text: str, limit: int) -> str:
    if limit <= 0:
        return ""
    if len(text) <= limit:
        return text
    remain = len(text) - limit
    return text[:limit] + f"\\n...[truncated {remain} chars]"


def _looks_like_policy_blocked_text(text: str) -> bool:
    t = (text or "").lower()
    patterns = (
        "allowlist policy",
        "策略拦截",
        "退出码 126",
        "exit code 126",
        "无法按你的约束完成",
        "无法读取",
    )
    return any(p in t for p in patterns)


def parse_shell_calls(response: Any) -> list[ShellCall]:
    """从 Responses API 返回中提取 shell_call。"""
    calls: list[ShellCall] = []
    for item in (_get_field(response, "output", []) or []):
        if _get_field(item, "type") != "shell_call":
            continue
        call_id = str(_get_field(item, "call_id", "") or "").strip()
        action = _get_field(item, "action", {}) or {}
        commands_raw = _get_field(action, "commands", []) or []
        commands = tuple(str(cmd).strip() for cmd in commands_raw if str(cmd).strip())
        max_output_length = _get_field(action, "max_output_length")
        if not isinstance(max_output_length, int):
            max_output_length = None
        timeout_ms = _get_field(action, "timeout_ms")
        if not isinstance(timeout_ms, int):
            timeout_ms = None
        if call_id and commands:
            calls.append(
                ShellCall(
                    call_id=call_id,
                    commands=commands,
                    max_output_length=max_output_length,
                    timeout_ms=timeout_ms,
                )
            )
    return calls


def is_command_allowed(command: str, allowed_prefixes: Sequence[str] = DEFAULT_ALLOWED_COMMAND_PREFIXES) -> bool:
    command = (command or "").strip()
    if not command:
        return False
    if any(snippet in command for snippet in DISALLOWED_SNIPPETS):
        return False
    try:
        tokens = shlex.split(command)
    except ValueError:
        return False
    if not tokens:
        return False
    cmd = tokens[0]
    if cmd not in set(allowed_prefixes):
        return False
    # 禁止 python -c/-m，避免执行任意内联代码。
    if cmd in {"python", "python3"} and len(tokens) >= 2 and tokens[1] in {"-c", "-m"}:
        return False
    return True


def run_shell_command(command: str, cwd: str | Path, timeout_sec: int = 30) -> ShellExecutionResult:
    """在本地执行单条允许的命令并返回执行结果。"""
    try:
        tokens = shlex.split(command)
    except ValueError as exc:
        return ShellExecutionResult(
            command=command,
            returncode=2,
            stdout="",
            stderr=f"invalid command syntax: {exc}",
        )

    completed = subprocess.run(
        tokens,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=timeout_sec,
        check=False,
    )
    return ShellExecutionResult(
        command=command,
        returncode=int(completed.returncode),
        stdout=completed.stdout or "",
        stderr=completed.stderr or "",
    )


def build_shell_call_output_items(
    call_results: dict[str, list[ShellExecutionResult]],
    max_output_length_by_call: dict[str, int] | None = None,
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    max_output_length_by_call = max_output_length_by_call or {}
    for call_id, results in call_results.items():
        call_limit = max_output_length_by_call.get(call_id, DEFAULT_SHELL_OUTPUT_CHAR_LIMIT)
        call_limit = max(200, min(int(call_limit), HARD_MAX_SHELL_OUTPUT_CHAR_LIMIT))
        half_limit = max(100, int(call_limit / 2))
        output_chunks: list[dict[str, Any]] = []
        for result in results:
            output_chunks.append(
                {
                    "stdout": _truncate_text(result.stdout, half_limit),
                    "stderr": _truncate_text(result.stderr, half_limit),
                    "outcome": {
                        "type": "exit",
                        "exit_code": int(result.returncode),
                    },
                }
            )
        item: dict[str, Any] = {
            "type": "shell_call_output",
            "call_id": call_id,
            "output": output_chunks,
        }
        max_len = max_output_length_by_call.get(call_id)
        if isinstance(max_len, int):
            item["max_output_length"] = max_len
        items.append(item)
    return items


def extract_response_text(response: Any) -> str:
    """提取模型最终文本输出。"""
    direct = _get_field(response, "output_text", "")
    if isinstance(direct, str) and direct.strip():
        return direct.strip()

    chunks: list[str] = []
    for item in (_get_field(response, "output", []) or []):
        if _get_field(item, "type") != "message":
            continue
        for part in (_get_field(item, "content", []) or []):
            txt = _get_field(part, "text", "")
            if txt:
                chunks.append(str(txt))
            output_txt = _get_field(part, "output_text", "")
            if output_txt:
                chunks.append(str(output_txt))
    return "\\n".join(chunks).strip()


def generate_semantic_tree_with_shell(
    *,
    client: Any,
    model: str,
    prompt: str,
    reference_image_path: str | None = None,
    cwd: str | Path,
    max_turns: int = 8,
    allowed_prefixes: Sequence[str] = DEFAULT_ALLOWED_COMMAND_PREFIXES,
) -> str:
    """执行 shell_call 循环，直到模型给出最终语义树文本。"""
    reference_image_file_id: str | None = None
    if reference_image_path:
        reference_image_file_id = upload_reference_image_file(client, reference_image_path)

    initial_input = build_initial_input(
        prompt=prompt,
        reference_image_path=reference_image_path,
        reference_image_file_id=reference_image_file_id,
    )
    response = client.responses.create(
        model=model,
        tools=[{"type": "shell"}],
        input=initial_input,
    )

    policy_retry_used = False

    for _ in range(max_turns):
        calls = parse_shell_calls(response)
        if not calls:
            text = extract_response_text(response)
            if text and not _looks_like_policy_blocked_text(text):
                return text
            if text and _looks_like_policy_blocked_text(text) and not policy_retry_used:
                policy_retry_used = True
                response = client.responses.create(
                    model=model,
                    previous_response_id=_get_field(response, "id"),
                    tools=[{"type": "shell"}],
                    input=(
                        "不要放弃。请继续并改用 allowlist 内的单命令重试："
                        "cat/jq/rg/ls/sed/head/tail/wc/python3(仅脚本文件，不可 -c/-m)。"
                        "禁止管道和重定向。先读取 EigenPhi/BlockSec/rule 文件，再输出完整业务语义树 Markdown。"
                    ),
                )
                continue
            if text:
                return text
            raise RuntimeError("模型返回中既没有 shell_call，也没有可提取文本，已中止以避免写出空文件。")

        call_results: dict[str, list[ShellExecutionResult]] = {}
        max_output_length_by_call: dict[str, int] = {}
        for call in calls:
            if isinstance(call.max_output_length, int):
                max_output_length_by_call[call.call_id] = call.max_output_length
            call_results.setdefault(call.call_id, [])

            timeout_sec = 30
            if isinstance(call.timeout_ms, int) and call.timeout_ms > 0:
                timeout_sec = max(1, int(call.timeout_ms / 1000))

            for command in call.commands:
                if not is_command_allowed(command, allowed_prefixes):
                    call_results[call.call_id].append(
                        ShellExecutionResult(
                            command=command,
                            returncode=126,
                            stdout="",
                            stderr=(
                                "command blocked by allowlist policy; "
                                "retry with a single command using allowed prefixes: "
                                "python3/python/jq/rg/ls/cat/sed/head/tail/wc; "
                                "do not use pipes/redirection/&&/||/; and do not use python -c/-m"
                            ),
                        )
                    )
                    continue

                local_result = run_shell_command(command, cwd=cwd, timeout_sec=timeout_sec)
                call_results[call.call_id].append(local_result)

        response = client.responses.create(
            model=model,
            previous_response_id=_get_field(response, "id"),
            tools=[{"type": "shell"}],
            input=build_shell_call_output_items(call_results, max_output_length_by_call=max_output_length_by_call),
        )

    # 兜底前先补齐未完成的 shell_call 输出，避免 API 报缺失 call_id。
    for _ in range(4):
        pending_calls = parse_shell_calls(response)
        if not pending_calls:
            break

        pending_results: dict[str, list[ShellExecutionResult]] = {}
        pending_max_output_len: dict[str, int] = {}
        for call in pending_calls:
            pending_results[call.call_id] = []
            if isinstance(call.max_output_length, int):
                pending_max_output_len[call.call_id] = call.max_output_length
            for command in call.commands:
                pending_results[call.call_id].append(
                    ShellExecutionResult(
                        command=command,
                        returncode=124,
                        stdout="",
                        stderr="terminated because max_turns reached before completion",
                    )
                )

        response = client.responses.create(
            model=model,
            previous_response_id=_get_field(response, "id"),
            tools=[{"type": "shell"}],
            input=build_shell_call_output_items(
                pending_results,
                max_output_length_by_call=pending_max_output_len,
            ),
        )

    # 兜底：达到最大轮次后，强制收敛为最终文本，避免直接失败。
    final_response = client.responses.create(
        model=model,
        previous_response_id=_get_field(response, "id"),
        input=(
            "停止调用任何工具。请基于当前已获得的证据直接输出最终 Markdown 业务语义结构树。"
            "要求：标题 TX Root、分阶段、中文、不要代码块、不要解释。"
        ),
    )
    final_text = extract_response_text(final_response)
    if final_text:
        return final_text

    raise RuntimeError("shell reasoning exceeded max_turns and final convergence produced empty output")
