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
