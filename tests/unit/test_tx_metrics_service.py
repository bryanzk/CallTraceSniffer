from decimal import Decimal

from calltrace.services.tx_metrics_service import TxMetricsService


class _StubEigenPhiClient:
    def __init__(self, payload):
        self._payload = payload

    def fetch_tx(self, tx_hash: str):
        return self._payload


class _StubDuneClient:
    def __init__(self, rows):
        self._rows = rows

    def fetch_rows(self, block_start, block_end, tx_hashes):
        return self._rows


class _StubRpcClient:
    def __init__(self, count):
        self._count = count

    def get_block_tx_count(self, block_number):
        return self._count


def test_analyze_batch_merges_sources():
    tx_hash = "0x" + "1" * 64
    eigenphi_payload = {
        "txMeta": {
            "blockNumber": 100,
            "blockMiner": "0xdef",
            "transactionIndex": 1,
            "transactionToAddress": "0xabc",
            "gasPrice": 10,
            "gasUsed": 2,
            "baseFeePerGas": 3,
        },
        "tokenFlows": [
            {
                "address": "0xabc",
                "tokenBalances": [
                    {
                        "tokenSpec": "PLATFORM",
                        "tokenAddress": "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee",
                        "tokenAmount": str(10**18),
                        "tokenVolume": "2000",
                    },
                ],
            },
        ],
        "tokenPrices": [
            {
                "tokenSpec": "PLATFORM",
                "tokenAddress": "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee",
                "priceInUsd": "2000",
            },
        ],
    }
    dune_rows = [
        {
            "tx_hash": tx_hash,
            "builder": "builder-x",
            "builder_address": "0xdef",
            "miner_tip_amount": Decimal("0.5"),
        },
    ]
    service = TxMetricsService(
        _StubEigenPhiClient(eigenphi_payload),
        _StubDuneClient(dune_rows),
        _StubRpcClient(123),
    )
    result = service.analyze_batch([tx_hash])

    assert result["ok"] is True
    assert result["block_start"] == 100
    assert result["block_end"] == 100

    row = result["results"][0]
    assert row["tx_hash"] == tx_hash
    assert row["gasUsed"] == 2
    assert row["builderTip"] == "0.000000000000000014"
    assert row["builderTipPerGas"] == "0.000000000000000007"
    assert row["coinbaseTransfer"] == "0.5"
    assert row["builderTipWithCT"] == "0.500000000000000014"
    assert row["revenueEth"] == "1"
    assert row["revenueUsd"] == "2000"
    assert row["revenueUsdAll"] == "2000"
    assert row["blockTxCount"] == 123


def test_analyze_batch_smoke_example_tx():
    tx_hash = "0x91742ef36b96731c1d371e4af2fccc3347e2fea7911151e808a66901e5467756"
    eigenphi_payload = {
        "txMeta": {
            "blockNumber": 24272267,
            "blockMiner": "0x396343362be2a4da1ce0c1c210945346fb82aa49",
            "transactionIndex": 128,
            "transactionToAddress": "0xa8b7643a8331fe18fb35642646aea7e993a747fc",
            "gasPrice": 31365590,
            "gasUsed": 1700457,
            "baseFeePerGas": 31365589,
        },
        "tokenFlows": [
            {
                "address": "0xa8b7643a8331fe18fb35642646aea7e993a747fc",
                "tokenBalances": [
                    {
                        "tokenSpec": "PLATFORM",
                        "tokenAddress": "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee",
                        "tokenAmount": "2876356082165525",
                        "tokenVolume": "9.154855018151237953",
                    },
                ],
            },
        ],
        "tokenPrices": [
            {
                "tokenSpec": "PLATFORM",
                "tokenAddress": "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee",
                "priceInUsd": "3182.79613394",
            },
        ],
    }
    dune_rows = [
        {
            "tx_hash": tx_hash,
            "builder": "0x396343362be2a4da1ce0c1c210945346fb82aa49",
            "builder_address": "0x396343362be2a4da1ce0c1c210945346fb82aa49",
            "miner_tip_amount": "0.000034047305653313",
        },
    ]
    service = TxMetricsService(
        _StubEigenPhiClient(eigenphi_payload),
        _StubDuneClient(dune_rows),
        _StubRpcClient(320),
    )
    result = service.analyze_batch([tx_hash])

    row = result["results"][0]
    assert row["blockNumber"] == 24272267
    assert row["gasUsed"] == 1700457
    assert row["blockIndex"] == 128
    assert row["botAddress"] == "0xa8b7643a8331fe18fb35642646aea7e993a747fc"
    assert row["builder"]["address"] == "0x396343362be2a4da1ce0c1c210945346fb82aa49"
    assert row["builder"]["name"] == "0x396343362be2a4da1ce0c1c210945346fb82aa49"
    assert row["builderTip"] == "0.000000000001700457"
    assert row["builderTipPerGas"] == "0.000000000000000001"
    assert row["coinbaseTransfer"] == "0.000034047305653313"
    assert row["builderTipWithCT"] == "0.00003404730735377"
    assert row["revenueEth"] == "0.002876356082165525"
    assert row["revenueUsd"] == "9.1548550181512379531504185"
    assert row["revenueUsdAll"] == "9.154855018151237953"
    assert row["blockTxCount"] == 320
