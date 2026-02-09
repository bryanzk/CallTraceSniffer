#!/usr/bin/env python3
"""使用 CoinMarketCap API 查询 wstETH 在指定 Unix 时间戳的 USD 价格。

用法:
  export COINMARKETCAP_API_KEY=你的API密钥
  python scripts/query_cmc_wsteth_at_time.py [unix_timestamp]

若省略 unix_timestamp，则使用区块 24270635 的链上时间戳 1768672451（2026-01-17 17:54:11 UTC）。

依赖: requests（pip install requests）
CMC API: /v2/tools/price-conversion 的 time 参数需要 Hobbyist 及以上；
         Basic 仅支持最新价，本脚本仍会尝试传入 time，若返回 403 则说明需升级。
"""
from __future__ import annotations

import os
import sys

def main() -> None:
    ts = "1768672451"
    if len(sys.argv) > 1:
        ts = sys.argv[1].strip()
    api_key = os.environ.get("COINMARKETCAP_API_KEY") or os.environ.get("CMC_PRO_API_KEY")
    if not api_key:
        print("错误: 请设置环境变量 COINMARKETCAP_API_KEY", file=sys.stderr)
        sys.exit(1)
    try:
        import requests
    except ImportError:
        print("错误: 需要 requests，请执行 pip install requests", file=sys.stderr)
        sys.exit(1)
    url = "https://pro-api.coinmarketcap.com/v2/tools/price-conversion"
    params = {"amount": 1, "symbol": "WSTETH", "time": ts, "convert": "USD"}
    headers = {"Accept": "application/json", "X-CMC_PRO_API_KEY": api_key}
    resp = requests.get(url, params=params, headers=headers, timeout=30)
    print(resp.text)
    if not resp.ok:
        sys.exit(2)

if __name__ == "__main__":
    main()
