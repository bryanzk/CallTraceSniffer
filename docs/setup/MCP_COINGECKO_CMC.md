# CoinGecko 与 CoinMarketCap MCP 配置说明

本文档说明如何在本项目中启用 **CoinGecko MCP** 与 **CoinMarketCap MCP**，用于获取 wstETH 等代币的时点/历史价格，以验证 MEV 交易的 PnL。

## 官方参考

- **CoinGecko MCP Server**：[https://docs.coingecko.com/docs/mcp-server](https://docs.coingecko.com/docs/mcp-server)
- **CoinMarketCap MCP**：[https://github.com/shinzo-labs/coinmarketcap-mcp](https://github.com/shinzo-labs/coinmarketcap-mcp)

---

## 1. CoinGecko MCP

### 方式一：远程公开服务（免 Key，推荐先试用）

在 Cursor 的 MCP 配置中增加：

```json
"coingecko_mcp": {
  "type": "http",
  "url": "https://mcp.api.coingecko.com/mcp",
  "enabled": true
}
```

- **端点**：`https://mcp.api.coingecko.com/mcp`（公开、免 Key）
- **限制**：共用限流，不适合高频调用；如需更高限流与历史数据，可使用 Pro 端点 + API Key。

### 方式二：Pro 端点（自带 Key）

若已持有一枚 CoinGecko Pro API Key，可改用：

```json
"coingecko_mcp": {
  "type": "http",
  "url": "https://mcp.pro-api.coingecko.com/mcp",
  "enabled": true
}
```

首次连接时按提示在浏览器中完成 Key 授权。

### 方式三：本地运行（需 Key）

```json
"coingecko_mcp_local": {
  "type": "local",
  "command": "npx",
  "args": ["-y", "@coingecko/coingecko-mcp"],
  "env": {
    "COINGECKO_PRO_API_KEY": "YOUR_PRO_API_KEY",
    "COINGECKO_ENVIRONMENT": "pro"
  },
  "enabled": true
}
```

Key 申请与档位见：[CoinGecko API Pricing](https://www.coingecko.com/en/api/pricing)。

---

## 2. CoinMarketCap MCP

需在 [CoinMarketCap](https://pro.coinmarketcap.com/signup/?plan=0) 申请免费 Basic API Key。

在 Cursor 的 MCP 配置中增加：

```json
"coinmarketcap": {
  "type": "local",
  "command": "npx",
  "args": ["-y", "@shinzolabs/coinmarketcap-mcp"],
  "env": {
    "COINMARKETCAP_API_KEY": "YOUR_COINMARKETCAP_API_KEY",
    "SUBSCRIPTION_LEVEL": "Basic"
  },
  "enabled": true
}
```

将 `YOUR_COINMARKETCAP_API_KEY` 替换为你的 Key。`SUBSCRIPTION_LEVEL` 与你在 CMC 的订阅一致（如 Hobbyist/Startup 等），Basic 即可使用 `cryptoQuotesLatest` 等基础工具；历史报价需 Hobbyist 及以上（如 `cryptoQuotesHistorical`）。

---

## 3. Cursor 中配置文件位置

- **macOS / Linux**：`~/.cursor/mcp.json` 或 `~/.cursor/config/mcp.json`
- **Windows**：`%USERPROFILE%\.cursor\mcp.json`

在对应文件的 `mcpServers` 里加入上述片段，保存后重启 Cursor 或重新加载 MCP。

---

## 4. 与本项目的配合使用

- **PnL 验证**：在 `docs/development/PNL_ANOMALY_0x082872cd.md` 中，使用 Crypto.com MCP 在区块时点取 ETH 价做验证；若启用 CoinGecko/CoinMarketCap MCP，可对同一笔交易用其工具取 wstETH/ETH 的时点或当前价做交叉验证。
- **取 wstETH 价格**：CoinGecko 的 coin id 为 `wrapped-steth`；CoinMarketCap 需先用 `cryptoCurrencyMap` 等查 wstETH 的 `id`/`slug`，再调 `cryptoQuotesLatest` 或（Hobbyist+）`cryptoQuotesHistorical` 按时间戳取价。

---

## 5. 已写入的配置

若已在全局 `~/.cursor/mcp.json` 中为本项目加入 CoinGecko / CoinMarketCap，则当前应包含：

- **coingecko_mcp**：远程公开 `https://mcp.api.coingecko.com/mcp`（免 Key）
- **coinmarketcap**：本地 `npx -y @shinzolabs/coinmarketcap-mcp`，需自行设置 `COINMARKETCAP_API_KEY`

请将 `YOUR_COINMARKETCAP_API_KEY` 换成真实 Key 后保存并重启 Cursor。
