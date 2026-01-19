"""
Smoke test for Dune Uniswap pool flags.
"""
import sys
import os

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'src'))

from calltrace.services.dune_service import DuneService


@pytest.mark.smoke
def test_smoke_unipool_dune_flags():
    tx_expected = {
        "0x7385f1d97d1adf8f2f4cbccd8e25e53c0f9b2444f3e01bd3602dc63fddab6edc": True,
        "0x2050b5a75fe34b56fac2a1eb5cf018a11b4eba71d15aa22a9b07b4d08622f641": True,
        "0xba86bf556ad0811c3f2aa384de600d4e78f0b8fe01814954110b7fab568f552c": False,
        "0x1d7cf317e928ed650b46a2533e4df9d9113a303a63d4f247fd87acfafb808d20": True,
    }

    rows = [
        {"tx_hash": tx_hash, "bool_used_uni": used}
        for tx_hash, used in tx_expected.items()
    ]

    class FakeClient:
        def __init__(self, api_key):
            self.api_key = api_key

        def get_latest_result(self, query_id, params=None):
            return {"result": {"rows": rows}}

    service = DuneService(api_key="dummy", client_factory=FakeClient)
    results = service.fetch_uniswap_flags(list(tx_expected.keys()))
    result_map = {item.tx_hash: item.bool_used_uni for item in results}

    for tx_hash, expected in tx_expected.items():
        assert result_map.get(tx_hash, False) == expected
