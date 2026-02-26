from calltrace.services.fourbyte_signatures import (
    build_selector_signature_map,
    extract_selectors_from_payload,
    normalize_selector,
)


def test_normalize_selector():
    assert normalize_selector("70a08231") == "0x70a08231"
    assert normalize_selector("0x70A08231") == "0x70a08231"
    assert normalize_selector("0x123") is None
    assert normalize_selector(123) is None


def test_extract_selectors_from_payload():
    payload = {
        "a": "70a08231",
        "b": {"x": "0xdd62ed3e", "y": "not_selector"},
        "c": ["0xabcdef12", "abcdef12", "0xabcdef12"],
    }
    selectors = extract_selectors_from_payload(payload)
    assert selectors == ["0x70a08231", "0xabcdef12", "0xdd62ed3e"]


def test_build_selector_signature_map_without_network(monkeypatch):
    def fake_lookup(selectors, timeout_sec=12, max_per_selector=5):
        out = {}
        for s in selectors:
            if s == "0x70a08231":
                out[s] = ["balanceOf(address)"]
            else:
                out[s] = []
        return out

    monkeypatch.setattr(
        "calltrace.services.fourbyte_signatures.lookup_selector_signatures",
        fake_lookup,
    )

    payload = {"selector": "0x70a08231", "other": ["0xdeadbeef"]}
    result = build_selector_signature_map(payload)
    assert result["selectors_total"] == 2
    assert result["selectors_resolved"] == 1
    assert result["mapping"]["0x70a08231"] == ["balanceOf(address)"]
    assert result["mapping"]["0xdeadbeef"] == []

