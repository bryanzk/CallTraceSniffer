import pytest

from calltrace.services.dune_service import DuneService, DuneQueryResult


class _FakeDuneClient:
    def __init__(self, api_key):
        self.api_key = api_key
        self.calls = []

    def get_latest_result(self, query_id, params=None):
        self.calls.append((query_id, params))
        return {
            "result": {
                "rows": [
                    {"tx_hash": "0x" + ("a" * 64), "bool_used_uni": True},
                    {"tx_hash": "0x" + ("b" * 64), "bool_used_uni": False},
                ]
            }
        }


def test_dune_service_fetches_and_parses_rows(monkeypatch):
    monkeypatch.setenv("DUNE_API_KEY", "test-key")
    service = DuneService(client_factory=_FakeDuneClient)
    results = service.fetch_uniswap_flags(["0x" + ("a" * 64), "0x" + ("b" * 64)])
    assert service._client.calls
    _, params = service._client.calls[0]
    assert params["tx_hashes"].startswith("(0x")
    assert params["tx_hashes"].count("),(") == 1
    assert results == [
        DuneQueryResult(tx_hash="0x" + ("a" * 64), bool_used_uni=True),
        DuneQueryResult(tx_hash="0x" + ("b" * 64), bool_used_uni=False),
    ]
