import base64
from pathlib import Path
from types import SimpleNamespace

from calltrace.services.openai_shell_semantic_mvp import (
    ShellExecutionResult,
    _looks_like_policy_blocked_text,
    build_initial_input,
    build_semantic_prompt,
    build_shell_call_output_items,
    is_command_allowed,
    parse_shell_calls,
)


def test_parse_shell_calls_extracts_valid_calls():
    response = SimpleNamespace(
        output=[
            SimpleNamespace(type="message"),
            SimpleNamespace(
                type="shell_call",
                call_id="c1",
                action=SimpleNamespace(commands=["jq . a.json"], max_output_length=1200, timeout_ms=5000),
            ),
            SimpleNamespace(
                type="shell_call",
                call_id="c2",
                action={"commands": ["python3 run.py"]},
            ),
            SimpleNamespace(type="shell_call", call_id="", action={"commands": ["echo bad"]}),
        ]
    )

    calls = parse_shell_calls(response)

    assert len(calls) == 2
    assert calls[0].call_id == "c1"
    assert calls[0].commands == ("jq . a.json",)
    assert calls[0].max_output_length == 1200
    assert calls[0].timeout_ms == 5000
    assert calls[1].call_id == "c2"
    assert calls[1].commands == ("python3 run.py",)
    assert calls[1].max_output_length is None


def test_is_command_allowed_checks_prefixes():
    prefixes = ("python3", "jq", "rg", "ls")

    assert is_command_allowed("python3 scripts/parse.py", prefixes)
    assert is_command_allowed(" jq '.a' data.json", prefixes)
    assert not is_command_allowed("rm -rf /", prefixes)
    assert not is_command_allowed("bash -lc 'python3 x.py'", prefixes)
    assert not is_command_allowed("python3 -c 'print(1)'", prefixes)


def test_build_shell_call_output_items_formats_result():
    call_results = {
        "call_1": [
            ShellExecutionResult(
                command="jq . sample.json",
                returncode=0,
                stdout='{"ok":true}\n',
                stderr="",
            )
        ],
        "call_2": [
            ShellExecutionResult(
                command="python3 bad.py",
                returncode=1,
                stdout="",
                stderr="Traceback...",
            )
        ],
    }

    items = build_shell_call_output_items(call_results, max_output_length_by_call={"call_1": 2000})

    assert len(items) == 2
    assert items[0]["type"] == "shell_call_output"
    by_call_id = {x["call_id"]: x for x in items}
    assert by_call_id["call_1"]["output"][0]["outcome"]["exit_code"] == 0
    assert by_call_id["call_1"]["output"][0]["stdout"] == '{"ok":true}\n'
    assert by_call_id["call_2"]["output"][0]["stderr"] == "Traceback..."
    assert by_call_id["call_1"]["max_output_length"] == 2000
    assert "max_output_length" not in by_call_id["call_2"]


def test_build_shell_call_output_items_truncates_long_streams():
    long_stdout = "A" * 500
    long_stderr = "B" * 500
    call_results = {
        "call_long": [
            ShellExecutionResult(
                command="cat huge.txt",
                returncode=0,
                stdout=long_stdout,
                stderr=long_stderr,
            )
        ]
    }
    # max_output_length=200 -> stdout/stderr 各约 100 字符
    items = build_shell_call_output_items(call_results, max_output_length_by_call={"call_long": 200})
    chunk = items[0]["output"][0]
    assert len(chunk["stdout"]) <= 140
    assert len(chunk["stderr"]) <= 140
    assert "truncated" in chunk["stdout"]


def test_build_semantic_prompt_contains_paths_and_target():
    prompt = build_semantic_prompt(
        eigenphi_json_path="local/sample0x8c/0x8c_eigenphi.json",
        blocksec_json_path="local/sample0x8c/0x8c_blocksec.json",
        rule_json_path="local/sample0x8c/phase_rule.json",
        reference_image_path="local/sample0x8c/8c.png",
        output_markdown_path="local/sample0x8c/semantic_tree.md",
    )

    assert "local/sample0x8c/0x8c_eigenphi.json" in prompt
    assert "local/sample0x8c/0x8c_blocksec.json" in prompt
    assert "local/sample0x8c/phase_rule.json" in prompt
    assert "local/sample0x8c/8c.png" in prompt
    assert "local/sample0x8c/semantic_tree.md" in prompt
    assert "业务语义结构树" in prompt


def test_build_initial_input_includes_image_when_provided(tmp_path: Path):
    image_path = tmp_path / "8c.png"
    image_path.write_bytes(b"\x89PNG\r\n\x1a\nfakepng")
    prompt = "分析语义树"

    initial_input = build_initial_input(prompt=prompt, reference_image_path=str(image_path))

    assert isinstance(initial_input, list)
    assert initial_input[0]["role"] == "user"
    content = initial_input[0]["content"]
    assert content[0]["type"] == "input_text"
    assert content[0]["text"] == prompt
    assert content[1]["type"] == "input_image"
    assert content[1]["image_url"].startswith("data:image/png;base64,")
    encoded = content[1]["image_url"].split(",", 1)[1]
    assert base64.b64decode(encoded).startswith(b"\x89PNG")


def test_build_initial_input_prefers_file_id_when_provided():
    prompt = "分析语义树"
    initial_input = build_initial_input(
        prompt=prompt,
        reference_image_path="local/sample0x8c/8c.png",
        reference_image_file_id="file_abc123",
    )

    content = initial_input[0]["content"]
    assert content[1]["type"] == "input_image"
    assert content[1]["file_id"] == "file_abc123"
    assert "image_url" not in content[1]


def test_policy_block_text_detection():
    assert _looks_like_policy_blocked_text("shell 执行被策略拦截，退出码 126")
    assert _looks_like_policy_blocked_text("allowlist policy")
    assert not _looks_like_policy_blocked_text("正常生成语义树")
