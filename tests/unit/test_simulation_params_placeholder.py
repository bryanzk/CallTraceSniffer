from pathlib import Path
import re


def test_simulation_params_placeholder_is_multiline():
    content = Path("templates/index.html").read_text(encoding="utf-8")
    match = re.search(r'id="simulation-params"[^>]*placeholder=(["\'])(.*?)\1', content)
    assert match, "simulation-params placeholder not found"
    placeholder = match.group(2)
    assert "chainID" in placeholder
    assert "txnCustom" in placeholder
    assert "&#10;" in placeholder
