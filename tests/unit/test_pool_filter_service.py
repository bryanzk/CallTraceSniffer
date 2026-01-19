import pytest

from calltrace.services.pool_filter_service import (
    PoolFilterStorage,
    PoolFilterService,
    TOPIC_TRANSFER,
    TOPIC_V3,
)
from calltrace.services.dune_service import DuneQueryResult


def _topic_addr(addr):
    return "0x" + addr.lower().replace("0x", "").rjust(64, "0")


def _build_trace(pool_addr, token_addr):
    return {
        "dataMap": {
            "1": {
                "nodeType": 1,
                "event": {
                    "contract": pool_addr,
                    "topics": [TOPIC_V3],
                    "logData": "0x",
                },
            },
            "2": {
                "nodeType": 1,
                "event": {
                    "contract": token_addr,
                    "topics": [
                        TOPIC_TRANSFER,
                        _topic_addr(pool_addr),
                        _topic_addr("0x00000000009e50a7ddb7a7b0e2ee6604fd120e49"),
                    ],
                    "logData": "0x01",
                },
            },
            "3": {
                "invocation": {
                    "address": pool_addr,
                    "fromAddress": "0x00000000009e50a7ddb7a7b0e2ee6604fd120e49",
                    "value": "0",
                }
            },
        }
    }


def test_storage_upsert_and_load_pool_set(tmp_path):
    db_path = tmp_path / "unipool.db"
    storage = PoolFilterStorage(str(db_path))
    storage.upsert_pools([
        {"pool_address": "0xabc", "project": "uniswap v3", "first_seen_time": "2024-03-01 00:00:00"},
        {"pool_address": "0xdef", "project": "uniswap v2", "first_seen_time": "2024-03-02 00:00:00"},
    ])
    pool_set = storage.load_pool_set()
    assert "0xabc" in pool_set
    assert "0xdef" in pool_set
    assert storage.get_pool_count() == 2


def test_storage_last_sync_time_defaults(tmp_path):
    db_path = tmp_path / "unipool.db"
    storage = PoolFilterStorage(str(db_path))
    assert storage.get_last_sync_time() == "1970-01-01 00:00:00"
    storage.set_last_sync_time("2024-03-05 00:00:00")
    assert storage.get_last_sync_time() == "2024-03-05 00:00:00"


def test_filter_trace_hits_pool_and_asset_flow(tmp_path):
    db_path = tmp_path / "unipool.db"
    storage = PoolFilterStorage(str(db_path))
    pool_addr = "0x4b2cde9effaa15999010e66da016b2b2c949f747"
    token_addr = "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"
    storage.upsert_pools([{
        "pool_address": pool_addr,
        "project": "uniswap v3",
        "first_seen_time": "2024-03-01 00:00:00",
    }])
    service = PoolFilterService(storage, extractor_factory=lambda: None)
    has_pool, matched = service.filter_trace(_build_trace(pool_addr, token_addr))
    assert has_pool is True
    assert pool_addr.lower() in matched


def test_filter_trace_no_pool(tmp_path):
    db_path = tmp_path / "unipool.db"
    storage = PoolFilterStorage(str(db_path))
    service = PoolFilterService(storage, extractor_factory=lambda: None)
    has_pool, matched = service.filter_trace({"dataMap": {}})
    assert has_pool is False
    assert matched == []


def test_check_tx_hashes_prefers_dune(monkeypatch, tmp_path):
    class FakeDuneService:
        def fetch_uniswap_flags(self, tx_hashes):
            return [
                DuneQueryResult(tx_hash=tx_hashes[0].lower(), bool_used_uni=True),
                DuneQueryResult(tx_hash=tx_hashes[1].lower(), bool_used_uni=False),
            ]

    db_path = tmp_path / "unipool.db"
    storage = PoolFilterStorage(str(db_path))
    service = PoolFilterService(storage, extractor_factory=lambda: None, dune_service=FakeDuneService())
    txs = ["0x" + ("a" * 64), "0x" + ("b" * 64)]
    results = service.check_tx_hashes(txs)
    assert results[0].has_uni_pool is True
    assert results[1].has_uni_pool is False
