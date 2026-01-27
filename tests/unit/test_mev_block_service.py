from calltrace.services.mev_block_service import build_mev_block_html, parse_block_mev_text


def test_parse_block_mev_text_basic():
    text = """
区块 123 MEV 汇总:
- 类型汇总:
  - Arbitrage: Profit 1.0 USD, Cost 0.1 USD, Revenue 1.1 USD
- 交易列表:
  - [0] 0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
    - Types: Arbitrage
    - Profit: 1.0 USD
    - Cost: 0.1 USD
    - Revenue: 1.1 USD
    - EigenPhi PnL: https://example.com/pnl
    - EigenTx: https://example.com/tx
"""
    result = parse_block_mev_text(text)
    assert result["block_number"] == 123
    assert len(result["transactions"]) == 1
    tx = result["transactions"][0]
    assert tx["index"] == 0
    assert tx["tx_hash"].startswith("0xaaaaaaaa")
    assert tx["types"] == ["Arbitrage"]
    assert tx["profit"] == "1.0"


def test_build_mev_block_html_embedded_includes_svg_path():
    tx_hash = "0x" + "a" * 64
    block_data = {
        "block_number": 123,
        "transactions": [
            {
                "index": 1,
                "tx_hash": tx_hash,
                "types": ["Arbitrage"],
                "profit": "1.0",
                "cost": "0.1",
                "revenue": "1.1",
            }
        ],
    }
    html = build_mev_block_html(block_data, embedded=True)
    expected_svg = f"/mev/block/123/{tx_hash[:20]}_flow.svg"
    assert expected_svg in html
