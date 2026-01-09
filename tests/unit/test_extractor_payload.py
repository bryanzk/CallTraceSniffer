"""
Unit tests for BlockSecExtractor payload parsing helpers.
"""
import sys
import os

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
