"""
Smoke test for tx metrics batch with EigenPhi revenue fields.
"""
import sys
import os

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "src"))

from calltrace.services.tx_metrics_service import RpcClient, TxMetricsService


class _StubEigenPhiClient:
    def __init__(self, payloads):
        self._payloads = payloads

    def fetch_tx(self, tx_hash: str):
        return self._payloads.get(tx_hash)


class _StubDuneClient:
    def fetch_rows(self, block_start, block_end, tx_hashes):
        return []


@pytest.mark.smoke
def test_smoke_tx_metrics_revenue_usd_all():
    rpc_url = os.getenv("ETH_RPC_URL")
    if not rpc_url:
        pytest.skip("ETH_RPC_URL 未配置，跳过真实 blockTxCount 校验")

    tx_hashes = [
        "0x24c756ce474adba064012854a9c4bc6bfac6d5046b4aed5142500950162e9a2f",
        "0x88f0faf0a8a2874b10f2acedff874e92eb0e7ea30195b6cccbb4bedb02618d68",
        "0x49f3b1c7e52cf18e7a3464cf1b4b4ab8862a8d0c440b333bec4d7bdae03916da",
    ]

    eigenphi_payloads = {
        tx_hashes[0]: {
            "txMeta": {
                "blockNumber": 24278160,
                "transactionToAddress": "0x313e8a9425bc393d8fea4de739320574501e8ebc",
            },
            "tokenFlows": [
                {
                    "address": "0x313e8a9425bc393d8fea4de739320574501e8ebc",
                    "tokenBalances": [
                        {
                            "tokenSpec": "PLATFORM",
                            "tokenAddress": "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee",
                            "tokenAmount": "41305729358517",
                            "tokenVolume": "0.123481223044542864",
                        },
                    ],
                },
            ],
            "tokenPrices": [
                {
                    "tokenSpec": "PLATFORM",
                    "tokenAddress": "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee",
                    "priceInUsd": "2989.44541017",
                },
            ],
        },
        tx_hashes[1]: {
            "txMeta": {
                "blockNumber": 24182471,
                "transactionToAddress": "0x1f2f10d1c40777ae1da742455c65828ff36df387",
            },
            "tokenFlows": [
                {
                    "address": "0x1f2f10d1c40777ae1da742455c65828ff36df387",
                    "tokenBalances": [
                        {
                            "tokenSpec": "PLATFORM",
                            "tokenAddress": "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee",
                            "tokenAmount": "320808351064698138",
                            "tokenVolume": "1030.913000420821412426",
                        },
                        {
                            "tokenSpec": "ERC20",
                            "tokenAddress": "0x1111111111111111111111111111111111111111",
                            "tokenVolume": "0.002248641836981940",
                        },
                    ],
                },
            ],
            "tokenPrices": [
                {
                    "tokenSpec": "PLATFORM",
                    "tokenAddress": "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee",
                    "priceInUsd": "3213.48554986",
                },
            ],
        },
        tx_hashes[2]: {
            "txMeta": {
                "blockNumber": 24273364,
                "transactionToAddress": "0x1f2f10d1c40777ae1da742455c65828ff36df387",
            },
            "tokenFlows": [
                {
                    "address": "0x1f2f10d1c40777ae1da742455c65828ff36df387",
                    "tokenBalances": [
                        {
                            "tokenSpec": "PLATFORM",
                            "tokenAddress": "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee",
                            "tokenAmount": "972150930829092815",
                            "tokenVolume": "3107.141236925129677970",
                        },
                        {
                            "tokenSpec": "ERC20",
                            "tokenAddress": "0x2222222222222222222222222222222222222222",
                            "tokenVolume": "2.053964250472636389",
                        },
                    ],
                },
            ],
            "tokenPrices": [
                {
                    "tokenSpec": "PLATFORM",
                    "tokenAddress": "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee",
                    "priceInUsd": "3196.15106913",
                },
            ],
        },
    }

    service = TxMetricsService(
        _StubEigenPhiClient(eigenphi_payloads),
        _StubDuneClient(),
        RpcClient(rpc_url=rpc_url),
    )

    result = service.analyze_batch(tx_hashes)
    assert result["ok"] is True
    assert result["block_start"] == 24182471
    assert result["block_end"] == 24278160

    result_map = {item["tx_hash"]: item for item in result["results"]}
    assert result_map[tx_hashes[0]]["revenueUsd"] == "0.12348122304454286404791789"
    assert result_map[tx_hashes[0]]["revenueUsdAll"] == "0.123481223044542864"
    assert result_map[tx_hashes[0]]["blockTxCount"] == 329

    assert result_map[tx_hashes[1]]["revenueUsd"] == "1030.913000420821412425848161"
    assert result_map[tx_hashes[1]]["revenueUsdAll"] == "1030.915249062658394366"
    assert result_map[tx_hashes[1]]["blockTxCount"] == 288

    assert result_map[tx_hashes[2]]["revenueUsd"] == "3107.141236925129677970251301"
    assert result_map[tx_hashes[2]]["revenueUsdAll"] == "3109.195201175602314359"
    assert result_map[tx_hashes[2]]["blockTxCount"] == 317
