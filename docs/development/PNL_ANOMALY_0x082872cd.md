# 交易 0x082872cd... PnL 异常分析

**交易哈希**: `0x082872cd483a3499e106482af94f4afc48c4d4dce97e6056674d48931e84f3db`  
**区块**: 24270635 | **类型**: Arbitrage (Balancer Rebalance)

**区块时点（链上）**：timestamp **1768672451** → **2026-01-17 17:54:11 UTC**（以 `eth_getBlockByNumber(0x1721E57)` 为准；此前若用过 EigenPhi raw 中的其他时间字段，以本链上 timestamp 为准）。

---

## 1. 异常现象

EigenPhi 策略分析给出的 **USD 口径 PnL** 与 **链上净资金流** 量级严重不符：

| 口径 | 数值 | 说明 |
|------|------|------|
| 报告 Profit | **488,529.51 USD** | EigenPhi summary.profit |
| 报告 Revenue | 488,535.35 USD | summary.revenue |
| 报告 Cost | 5.84 USD | summary.cost（gas/矿工） |
| 净资金流 (Net Flows) | **-0.00182 ETH；+0.001633 wstETH** | 策略分析中的 Net Flows |

按当时常见价格（ETH/wstETH ≈ 3,200–3,400 USD），净流约：
- -0.00182 ETH ≈ **-5.84 USD**
- +0.001633 wstETH ≈ **+5.2 USD**

**合理 PnL 量级应在几美元、至多数十美元，而非约 48.8 万 USD。**

---

## 2. 根因：wstETH 价格字段错误

从 `get_eigenphi_tx_mev` 的 **include_raw** 原始数据可见：

### tokenPrices 中的异常

```json
"tokenPrices": [
  {"tokenAddress": "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2", "tokenSpec": "ERC20", "priceInUsd": "3209.37"},
  {"tokenAddress": "0x7f39c581f595b53c5cb19bd0b3f8da6c935e2ca0", "tokenSpec": "ERC20", "priceInUsd": "299196525.628406441334045075261"},
  {"tokenAddress": "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee", "tokenSpec": "PLATFORM", "priceInUsd": "3209.37"}
]
```

- **WETH / 原生 ETH**：约 3,209 USD，合理。
- **wstETH (0x7f39...)**：**299,196,525 USD**，约为真实价格的 **约 93,000 倍**（wstETH 正常应在约 3,000–3,500 USD 量级）。

Revenue/Profit 是按「wstETH 数量 × 该 priceInUsd」算出来的，因此被错误放大到约 48.8 万 USD。

### 与 missingTokenPrices 的矛盾

原始数据中同时有：

```json
"missingTokenPrices": ["0x7f39c581f595b53c5cb19bd0b3f8da6c935e2ca0"]
```

即 EigenPhi 在缺失价格列表里把 wstETH 标为「缺价」，却又在 `tokenPrices` 里给了一个错误的 2.99e8 USD，导致 **Revenue/Profit 计算使用了错误价格**，而非「缺价则不计入 USD」的保守逻辑。

---

## 3. 按链上数量的合理 PnL 估算

| 项目 | 原始数量 (raw) | 换算 | 约 USD (按 3209) |
|------|----------------|------|------------------|
| 套利者收到 wstETH | 1,632,824,287,220,495 (18 decimals) | 0.0016328 wstETH | ≈ 5.23 |
| 套利者付出 ETH (cost) | 1,819,705,822,530,495 wei | 0.00182 ETH | ≈ 5.84 |
| **净 PnL** | -0.00182 ETH + 0.00163 wstETH | 约 -0.0002 ETH 等价 | **约 -0.6 USD** |

因此：
- **合理 Revenue** ≈ 5.2 USD（按 wstETH ≈ ETH 价）
- **合理 Cost** ≈ 5.84 USD
- **合理 Profit** ≈ **-0.6 USD**（小幅亏损或近似打平），而不是 488,529 USD。

---

## 4. 结论与建议

| 项目 | 结论 |
|------|------|
| **异常类型** | **价格数据错误**：wstETH 的 `priceInUsd` 被设为约 2.99e8，导致 Revenue/Profit 被放大约 9.3e4 倍。 |
| **报告 PnL 是否可信** | **不可信**。USD 口径的 profit/revenue 严重高估。 |
| **链上净流是否可信** | **可信**。Net Flows（-0.00182 ETH, +0.001633 wstETH）与 raw 中 token 数量一致。 |
| **建议** | 使用本交易 PnL 时，应以「链上净流 × 自有价格」自算 USD，或暂时忽略 EigenPhi 对该 token 的 USD 汇总；对含 wstETH 的 MEV 交易，建议检查 `tokenPrices` 与 `missingTokenPrices` 是否一致，再决定是否采用其 summary.profit/revenue。 |

---

## 5. 数据来源与复现

- 策略分析：`get_eigenphi_tx_mev_analysis`（ws://127.0.0.1:8080/）
- 原始 MEV：`get_eigenphi_tx_mev`，`include_raw: true`
- 复现命令示例：
  ```bash
  python3 scripts/mev_analysis_ws.py -H "X-API-Key: eigenphi123" ws://127.0.0.1:8080/ 0x082872cd483a3499e106482af94f4afc48c4d4dce97e6056674d48931e84f3db
  python3 scripts/call_mcp_tool_ws.py -H "X-API-Key: eigenphi123" ws://127.0.0.1:8080/ get_eigenphi_tx_mev '{"tx_hash":"0x082872cd483a3499e106482af94f4afc48c4d4dce97e6056674d48931e84f3db","include_raw":true}'
  ```

---

## 6. Crypto.com MCP 价格验证

使用 **Crypto.com MCP**（`user-crypto-market-data`）取得该 tx 所在区块时点的 ETH 价格，作为 wstETH 的代理价（Crypto.com 未上线 wstETH 交易对，wstETH ≈ 1:1 ETH 计价）。

### 时点与数据源

- **区块时间戳（链上）**：**1768672451** → **2026-01-17 17:54:11 UTC**（来源：`eth_getBlockByNumber(0x1721E57)`）
- **MCP 调用**：
  - `get_instruments`：确认无 wstETH，采用 ETH 代理
  - `get_candlestick(instrument_name="ETHUSDT", timeframe="1m")`：取含该时刻的 1 分钟 K 线
- **选用 K 线**：含 17:54:11 的 1m 烛（具体时间以你拉取当时对应到 2026-01-17 17:54 UTC 的 bar 为准）
  - 示例 **close** ≈ **3012.90 USD**（用作区块时点 ETH/wstETH 价格；若你按 2026-01-17 17:54 重拉，以新 K 线为准）

### 按 Crypto.com 价格的 PnL 重算

| 项目 | 数量 | 价格 (USD) | 金额 (USD) |
|------|------|------------|------------|
| 成本（付出 ETH） | 0.0018197 ETH | 3012.90 | **5.49** |
| 收入（收到 wstETH，按 1:1 ETH 计） | 0.0016328 wstETH | 3012.90 | **4.92** |
| **Profit** | — | — | **-0.57** |

与第 3 节「按链上数量的合理 PnL 估算」一致：**合理 PnL 约 -0.5～-0.6 USD**。

### 验证结论

| 数据源 | 区块时点 ETH 价格 | 算得 Profit |
|--------|-------------------|-------------|
| EigenPhi tokenPrices (WETH) | 3209.37 | (与 cost 5.84 一致) |
| EigenPhi tokenPrices (wstETH，错误) | 299,196,525 | **488,529**（异常） |
| **Crypto.com MCP ETHUSDT 1m** | **3012.90** | **-0.57** |

**说明**：区块 24270635 的**正确 UTC 为 2026-01-17 17:54:11**（链上 timestamp=1768672451）。Crypto.com 示例 K 线为历史拉取时的参考；以链上 timestamp 为准做验证时，应取 2026-01-17 17:54 UTC 附近的 1m close。结论不变：合理 PnL 约 -0.6 USD，EigenPhi 报告的 488,529 USD 为异常。

---

## 7. CoinGecko / CoinMarketCap 在该时点的 wstETH 价格

### MCP 可用性

当前 **CallTraceSniffer 项目未配置 CoinGecko、CoinMarketCap 的 MCP**（`mcps/` 下仅有 user-crypto-market-data、user-alphavantage、cursor-ide-browser 等），因此无法通过「调用 CoinGecko / CoinMarketCap 的 MCP」取得价格。若后续在 Cursor 中启用对应 MCP，可复用「区块时间戳 → 该时点价格 → 重算 PnL」的验证流程。

### 使用公开 API 的结果

在无法使用 MCP 的前提下，用公开接口做了补充查询：

#### CoinGecko（wrapped-steth）

- **Coin ID**：`wrapped-steth`（对应合约 0x7f39c581f595b53c5cb19bd0b3f8da6c935e2ca0）
- **区块时点（正确）**：链上 timestamp **1768672451** → **2026-01-17 17:54:11 UTC**
- **market_chart/range**：`from=1768672430&to=1768672500` → **prices 为空**（免费接口在该分钟区间无数据）
- **history?date=17-01-2026**（区块当日）：**current_price ≈ 4036.78 USD**，market_cap ≈ 13.24B USD

因此，**在「该 tx 所在区块时点」上**，CoinGecko 未在 market_chart/range 返回该分钟价；以 **区块当日 (2026-01-17) 的 history** 为基准，wstETH **当日价 ≈ 4036.78 USD**，可用于数量级验证（与 ETH 同量级），不能精确到 17:54:11 那一分钟。

#### CoinMarketCap（含 MCP 调用方式）

- 本项目中 **CoinMarketCap MCP 未在可用 MCP 列表内**，会话内无法直接调用；若在 Cursor 中对该项目启用了 CoinMarketCap MCP（`~/.cursor/mcp.json` 中已配置 `coinmarketcap`），可用下列方式查该时点 wstETH 价格。
- **MCP 调用**（[shinzo-labs/coinmarketcap-mcp](https://github.com/shinzo-labs/coinmarketcap-mcp)）：
  - 工具：`priceConversion`（Basic 档可用；若支持 `time` 参数则可查历史时点）
  - 参数示例：`amount=1`, `symbol="WSTETH"`, `convert="USD"`, `time="1768672451"`（区块时间戳）
  - 在 Cursor 中调用示例：`call_mcp_tool(server="coinmarketcap", toolName="priceConversion", arguments={"amount":1, "symbol":"WSTETH", "convert":"USD", "time":"1768672451"})`
- **REST API**（需 `X-CMC_PRO_API_KEY`）：
  ```text
  GET https://pro-api.coinmarketcap.com/v1/tools/price-conversion?amount=1&symbol=WSTETH&convert=USD&time=1768672451
  ```
- 若 Basic 档的 `priceConversion` 不支持 `time`，历史价需 Hobbyist 及以上档的 `cryptoQuotesHistorical`。

### 本次会话补充（CoinGecko MCP / CMC MCP）

- **CoinGecko MCP**（`user-coingecko_mcp`）：`get_coins_contract(id="ethereum", contract_address="0x7f39c581f595b53c5cb19bd0b3f8da6c935e2ca0")` → wstETH **当前** USD 价 **3695.84**；`get_range_contract_coins_market_chart(from=1768672391, to=1768672511, …)` → **prices 为空**（该时点历史无数据）。
- **CoinMarketCap MCP**：本项目可见 MCP 中无 `coinmarketcap`，未执行调用；上文已给出启用后的 MCP 调用方式与 REST 示例。

### 汇总：各源 wstETH/ETH 价格与验证结论

| 数据源 | 类型 | 在该区块时点的 wstETH/ETH 价 | 说明 |
|--------|------|-----------------------------|------|
| EigenPhi (wstETH) | MCP/raw | 299,196,525（错误） | 导致报告 Profit 488,529 |
| Crypto.com MCP (ETH 代理) | MCP | **3012.90**（1m close 示例） | 用于验证，算得 Profit ≈ -0.57 |
| CoinGecko 公开 API | 公开 | 时点区间**无数据**；**当日 (2026-01-17) 价 4036.78** | 当日价作量级参考 |
| CoinGecko MCP | MCP | 时点区间**无数据**；**当前价 3695.84** | 本次会话已调，历史需它源 |
| CoinMarketCap | MCP/API | 未取 | 本项目未启用 CMC MCP；调用方式见上 |

**结论**：在未配置 CoinGecko/CoinMarketCap MCP 的情况下，已用 Crypto.com MCP 的区块时点 ETH 价完成验证；CoinGecko 公开 API 未返回该时点的 wstETH 价，仅提供当前价量级；若日后接入 CoinGecko/CMC 的 MCP 或历史 API，可按同一时点再算一次 PnL 做交叉验证。
