from calltrace.services.blocksec_adapter import (
    get_playwright_extractor_class,
    parse_simulation_url_tuple,
    sanitize_payload,
)


def test_blocksec_adapter_loads_external_extractor_class():
    cls = get_playwright_extractor_class()
    assert hasattr(cls, "extract_blocksec_data")
    assert hasattr(cls, "extract_blocksec_simulation_data")


def test_blocksec_adapter_parse_simulation_url_tuple():
    tx = "0x" + ("1" * 64)
    url = f"https://app.blocksec.com/explorer/tx/eth/{tx}?event=simulation&type=0"
    parsed_tx, normalized = parse_simulation_url_tuple(url)
    assert parsed_tx == tx
    assert normalized == url


def test_blocksec_adapter_sanitize_payload():
    raw = {
        "success": True,
        "tx_hash": "0x" + ("1" * 64),
        "trace_data": {"dataMap": {}, "mainTrace": []},
    }
    clean = sanitize_payload(raw)
    assert "trace_data" in clean
    assert "success" not in clean
