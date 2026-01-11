"""
Unit tests for BlockSec -> IR V1 mapping helpers.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'src'))

from calltrace.config import config
from calltrace.services import ir_v1_blocksec as v1


def _topic_for_address(addr):
    clean = addr.lower().replace("0x", "")
    return "0x" + ("0" * 24) + clean


def _transfer_log(token_addr, from_addr, to_addr, amount):
    return {
        "address": token_addr.lower(),
        "topics": [
            v1.TOPIC_TRANSFER,
            _topic_for_address(from_addr),
            _topic_for_address(to_addr),
        ],
        "data": hex(amount),
    }


def test_protocol_from_logs_priority():
    pool = "0x1111111111111111111111111111111111111111"
    logs = [
        {"address": pool, "topics": [v1.TOPIC_V3]},
        {"address": pool, "topics": [v1.TOPIC_V4]},
    ]
    assert v1._protocol_from_logs(logs, pool, "") == 4
    assert v1._protocol_from_logs([], pool, "0x022c0d9f") == 2


def test_infer_tokens_from_transfer_logs():
    pool = "0x2222222222222222222222222222222222222222"
    token_in = config.USDC
    token_out = config.WETH
    recipient = "0x3333333333333333333333333333333333333333"
    logs = [
        _transfer_log(token_in, "0xaaaa", pool, 123),
        _transfer_log(token_out, pool, recipient, 456),
    ]
    t_in, t_out, amt_in, amt_out, rec = v1._infer_tokens_from_transfers(logs, pool)
    assert t_in == token_in.lower()
    assert t_out == token_out.lower()
    assert amt_in == 123
    assert amt_out == 456
    assert rec == recipient.lower()


def test_extract_swap_v3_rounds_weth_output():
    pool = "0x4444444444444444444444444444444444444444"
    logs = [
        _transfer_log(config.USDC, "0xaaaa", pool, 1000),
        _transfer_log(config.WETH, pool, "0xbbbb", 257),
    ]
    invocation = {
        "address": pool,
        "decodedMethod": {
            "name": "swap",
            "signature": "0x128acb08",
            "callParams": [{"name": "zeroForOne", "value": True}],
            "returnParams": [
                {"name": "amount0", "value": "-1000"},
                {"name": "amount1", "value": "257"},
            ],
        },
    }
    swap = v1._extract_swap(invocation, logs, {pool}, dict(v1.TOKEN_DECIMALS))
    intent = swap["swapIntent"]
    assert intent["tokenIn"] == config.USDC.lower()
    assert intent["tokenOut"] == config.WETH.lower()
    assert intent["amountInBig"] == 1000
    assert intent["amountOutBig"] == 256


def test_extract_swap_v4_pool_id_and_tokens():
    pool = v1.V4_POOL_MANAGER
    topic_pool_id = "0x" + ("a" * 64)
    logs = [
        {"address": pool, "topics": [v1.TOPIC_V4, topic_pool_id]},
    ]
    invocation = {
        "address": pool,
        "decodedMethod": {
            "name": "swap",
            "callParams": [
                {
                    "name": "key",
                    "value": [
                        {"name": "currency0", "value": config.USDC},
                        {"name": "currency1", "value": config.WETH},
                    ],
                },
                {
                    "name": "params",
                    "value": [{"name": "zeroForOne", "value": True}],
                },
            ],
            "returnParams": [],
        },
    }
    swap = v1._extract_swap(invocation, logs, {pool}, dict(v1.TOKEN_DECIMALS))
    intent = swap["swapIntent"]
    assert intent["protocolId"] == 4
    expected_pool_id = v1._canonical_pool_id(f"{pool}|{topic_pool_id}")
    assert intent["poolId"] == expected_pool_id
    assert intent["tokenIn"] == config.USDC.lower()
    assert intent["tokenOut"] == config.WETH.lower()
    assert swap["executionArgs"]["recipientType"] == 1


def test_build_blocksec_ir_empty():
    ir = v1.build_blocksec_ir({}, "0x123")
    assert ir["tx_hash"] == "0x123"
    assert ir["rootTrace"]["type"] == "unknown"


def test_build_blocksec_ir_minimal_swap():
    pool = "0x5555555555555555555555555555555555555555"
    logs = [
        _transfer_log(config.USDC, "0xaaaa", pool, 1000),
        _transfer_log(config.WETH, pool, "0xbbbb", 500),
    ]
    trace_data = {
        "tx_hash": "0xabc",
        "dataMap": {
            "1": {
                "invocation": {
                    "address": pool,
                    "decodedMethod": {"name": "swap", "callParams": []},
                }
            },
            "2": {"nodeType": 1, "event": {"contract": logs[0]["address"], "topics": logs[0]["topics"], "logData": logs[0]["data"]}},
            "3": {"nodeType": 1, "event": {"contract": logs[1]["address"], "topics": logs[1]["topics"], "logData": logs[1]["data"]}},
        },
        "mainTrace": [{"id": 1, "children": []}],
    }
    ir = v1.build_blocksec_ir(trace_data, trace_data["tx_hash"])
    assert ir["tx_hash"] == trace_data["tx_hash"]
    assert ir["rootTrace"]["type"] == "swap"


def test_build_blocksec_ir_applies_extra_payloads():
    pool = "0x1111111111111111111111111111111111111111"
    token_in = "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    token_out = "0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
    in_amount = 1000 * (10 ** 6)
    out_amount = 5 * (10 ** 17)
    log_in = _transfer_log(token_in, "0x2222222222222222222222222222222222222222", pool, in_amount)
    log_out = _transfer_log(token_out, pool, "0x3333333333333333333333333333333333333333", out_amount)
    trace_data = {
        "tx_hash": "0xabc",
        "dataMap": {
            "1": {
                "invocation": {
                    "address": pool,
                    "decodedMethod": {"name": "swap", "callParams": []},
                }
            },
            "2": {"nodeType": 1, "event": {"contract": log_in["address"], "topics": log_in["topics"], "logData": log_in["data"]}},
            "3": {"nodeType": 1, "event": {"contract": log_out["address"], "topics": log_out["topics"], "logData": log_out["data"]}},
        },
        "mainTrace": [{"id": 1, "children": []}],
    }
    extra = {
        "token_info": [
            {"address": token_in, "decimals": 6},
            {"address": token_out, "decimals": 18},
        ],
        "fundflow": [
            {"to": pool, "token": token_in, "amount": "1000"},
            {"from": pool, "token": token_out, "amount": "0.5"},
        ],
        "basic_info": {"callData": "0xdeadbeef"},
    }

    ir = v1.build_blocksec_ir(trace_data, trace_data["tx_hash"], extra)
    intent = ir["rootTrace"]["swap"]["swapIntent"]
    assert intent["tokenIn"] == token_in
    assert intent["tokenOut"] == token_out
    assert intent["tokenInDecimals"] == 6
    assert intent["tokenOutDecimals"] == 18
    assert intent["amountInBig"] == in_amount
    assert intent["amountOutBig"] == out_amount
    assert intent["amountIn"] == 1000
    assert intent["amountOut"] == 0.5
    assert ir["rootTrace"]["encoded"] == "0xdeadbeef"


def test_apply_address_label_overrides_sets_protocol_id():
    pool_v3 = "0x1111111111111111111111111111111111111111"
    pool_v2 = "0x2222222222222222222222222222222222222222"
    root_trace = {
        "type": "swap",
        "swap": {"swapIntent": {"poolId": pool_v3, "protocolId": 0}},
        "callback": [
            {
                "type": "swap",
                "swap": {"swapIntent": {"poolId": pool_v2, "protocolId": 0}},
                "callback": [],
            }
        ],
    }
    labels = [
        {"address": pool_v3, "label": "Uniswap V3: pool"},
        {"address": pool_v2, "label": "0x2222_UNI-V2"},
    ]

    v1._apply_address_label_overrides(root_trace, labels)
    assert root_trace["swap"]["swapIntent"]["protocolId"] == 3
    assert root_trace["callback"][0]["swap"]["swapIntent"]["protocolId"] == 2


def test_apply_address_label_overrides_does_not_override_known():
    pool = "0x3333333333333333333333333333333333333333"
    root_trace = {
        "type": "swap",
        "swap": {"swapIntent": {"poolId": pool, "protocolId": 2}},
        "callback": [],
    }
    labels = [{"address": pool, "label": "Uniswap V3: pool"}]
    v1._apply_address_label_overrides(root_trace, labels)
    assert root_trace["swap"]["swapIntent"]["protocolId"] == 2


def test_apply_fundflow_overrides_prefers_largest_and_sets_decimals():
    pool = "0x4444444444444444444444444444444444444444"
    token_in = "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    token_out = "0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
    root_trace = {
        "type": "swap",
        "swap": {
            "swapIntent": {
                "poolId": pool,
                "protocolId": 3,
                "tokenIn": "unknown",
                "tokenOut": "",
                "amountInBig": 0,
                "amountOutBig": 0,
            }
        },
        "callback": [],
    }
    fundflow = [
        {"to": pool, "token": token_in, "amount": "1.23E3"},
        {"to": pool, "token": token_in, "amount": "1,234.5"},
        {"from": pool, "token": token_out, "amount": "2.5"},
    ]
    token_decimals = v1._build_token_decimals_map(
        [{"address": token_in, "decimals": 6}, {"address": token_out, "decimals": 18}]
    )

    v1._apply_fundflow_overrides(root_trace, fundflow, token_decimals)
    intent = root_trace["swap"]["swapIntent"]
    assert intent["tokenIn"] == token_in.lower()
    assert intent["tokenOut"] == token_out.lower()
    assert intent["tokenInDecimals"] == 6
    assert intent["tokenOutDecimals"] == 18
    assert intent["amountInBig"] == 1234500000
    assert intent["amountOutBig"] == 2500000000000000000


def test_apply_fundflow_overrides_skips_unknown_decimals():
    pool = "0x5555555555555555555555555555555555555555"
    token_in = "0xcccccccccccccccccccccccccccccccccccccccc"
    root_trace = {
        "type": "swap",
        "swap": {"swapIntent": {"poolId": pool, "protocolId": 3, "tokenIn": "unknown", "amountInBig": 0}},
        "callback": [],
    }
    fundflow = [{"to": pool, "token": token_in, "amount": "100"}]
    token_decimals = v1._build_token_decimals_map([])

    v1._apply_fundflow_overrides(root_trace, fundflow, token_decimals)
    intent = root_trace["swap"]["swapIntent"]
    assert intent["tokenIn"] == "unknown"
    assert intent["amountInBig"] == 0
