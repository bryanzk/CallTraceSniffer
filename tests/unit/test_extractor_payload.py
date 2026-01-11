"""
Unit tests for BlockSecExtractor payload parsing helpers.
"""
import sys
import os
import asyncio

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'src'))

from calltrace.services.extractor import BlockSecExtractor


def test_find_trace_payload_top_level():
    payload = {"dataMap": {"1": {}}, "mainTrace": []}
    found = BlockSecExtractor._find_trace_payload(payload)
    assert found == payload


def test_find_trace_payload_nested_data():
    payload = {"data": {"dataMap": {"1": {}}, "mainTrace": [{"id": 1}]}}
    found = BlockSecExtractor._find_trace_payload(payload)
    assert found == payload["data"]


def test_find_trace_payload_nested_result():
    payload = {"result": {"dataMap": {"1": {}}, "mainTrace": [{"id": 1}]}}
    found = BlockSecExtractor._find_trace_payload(payload)
    assert found == payload["result"]


def test_find_trace_payload_none():
    payload = {"data": {"foo": "bar"}}
    assert BlockSecExtractor._find_trace_payload(payload) is None


def test_update_payloads_from_response_collects_blocksec_payloads():
    collected = {}
    BlockSecExtractor._update_payloads_from_response(
        "https://app.blocksec.com/api/v1/onchain/tx/trace",
        {"dataMap": {"1": {}}, "mainTrace": []},
        collected,
    )
    assert "trace_data" in collected

    BlockSecExtractor._update_payloads_from_response(
        "https://app.blocksec.com/api/v1/onchain/tx/fundflow",
        {"data": [{"id": 1}]},
        collected,
    )
    assert collected["fundflow"] == [{"id": 1}]

    BlockSecExtractor._update_payloads_from_response(
        "https://app.blocksec.com/api/v1/onchain/tx/balance-change",
        {"result": [{"id": 2}]},
        collected,
    )
    assert collected["balance_change"] == [{"id": 2}]

    BlockSecExtractor._update_payloads_from_response(
        "https://app.blocksec.com/api/v1/onchain/tx/token-info",
        [{"address": "0x1"}],
        collected,
    )
    assert collected["token_info"] == [{"address": "0x1"}]

    BlockSecExtractor._update_payloads_from_response(
        "https://app.blocksec.com/api/v1/onchain/tx/address-label",
        [{"address": "0x2"}],
        collected,
    )
    assert collected["address_label"] == [{"address": "0x2"}]

    BlockSecExtractor._update_payloads_from_response(
        "https://app.blocksec.com/api/v1/onchain/tx/basic-info",
        {"data": {"txnHash": "0xabc"}},
        collected,
    )
    assert collected["basic_info"] == {"txnHash": "0xabc"}

    BlockSecExtractor._update_payloads_from_response(
        "https://app.blocksec.com/api/v1/onchain/tx/gas-flame",
        {"data": [{"name": "Total Gas"}]},
        collected,
    )
    assert collected["gas_flame"] == [{"name": "Total Gas"}]

    BlockSecExtractor._update_payloads_from_response(
        "https://app.blocksec.com/api/v1/onchain/tx/attack-event",
        {"data": [{"level": "high"}]},
        collected,
    )
    assert collected["attack_event"] == [{"level": "high"}]

    BlockSecExtractor._update_payloads_from_response(
        "https://app.blocksec.com/api/v1/onchain/tx/top-profit-loss",
        {"result": [{"token": "0x1"}]},
        collected,
    )
    assert collected["top_profit_loss"] == [{"token": "0x1"}]

    BlockSecExtractor._update_payloads_from_response(
        "https://app.blocksec.com/api/v1/onchain/tx/state-change",
        [{"contract": "0x2"}],
        collected,
    )
    assert collected["state_change"] == [{"contract": "0x2"}]


def test_extract_blocksec_data_success(monkeypatch):
    extractor = BlockSecExtractor()
    payloads = {
        "trace_data": {"dataMap": {}, "mainTrace": []},
        "fundflow": [{"id": 1}],
    }

    async def fake_extract(self, url):
        return payloads

    monkeypatch.setattr(BlockSecExtractor, "_extract_trace_from_page", fake_extract)
    result = asyncio.run(extractor.extract_blocksec_data("0x" + "1" * 64))
    assert result["success"] is True
    assert result["trace_data"] == payloads["trace_data"]
    assert result["fundflow"] == [{"id": 1}]


def test_extract_blocksec_data_missing_trace(monkeypatch):
    extractor = BlockSecExtractor()

    async def fake_extract(self, url):
        return {"fundflow": [{"id": 1}]}

    monkeypatch.setattr(BlockSecExtractor, "_extract_trace_from_page", fake_extract)
    result = asyncio.run(extractor.extract_blocksec_data("0x" + "2" * 64))
    assert result["success"] is False
    assert result["error"] == "未找到trace数据"


def test_extract_blocksec_simulation_data_success(monkeypatch):
    extractor = BlockSecExtractor()
    payloads = {"trace_data": {"dataMap": {}, "mainTrace": []}}

    async def fake_extract(self, url):
        return payloads

    monkeypatch.setattr(BlockSecExtractor, "_extract_trace_from_page", fake_extract)
    sim_url = "https://app.blocksec.com/explorer/tx/eth/0x" + ("3" * 64) + "?event=simulation&type=0"
    result = asyncio.run(extractor.extract_blocksec_simulation_data(sim_url))
    assert result["success"] is True
    assert result["trace_data"] == payloads["trace_data"]


def test_extract_blocksec_simulation_data_missing_trace(monkeypatch):
    extractor = BlockSecExtractor()

    async def fake_extract(self, url):
        return {}

    monkeypatch.setattr(BlockSecExtractor, "_extract_trace_from_page", fake_extract)
    sim_url = "https://app.blocksec.com/explorer/tx/eth/0x" + ("4" * 64) + "?event=simulation&type=0"
    result = asyncio.run(extractor.extract_blocksec_simulation_data(sim_url))
    assert result["success"] is False
    assert result["error"] == "未找到simulation trace数据"
