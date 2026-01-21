# TX Metrics API 使用说明

本文档说明线上 API 的调用方式、返回字段与数据来源/计算方法。

## 1. 基础信息

- **Base URL**: `https://calltracesniffer-production.up.railway.app`
- **Endpoint**: `POST /api/tx-metrics-batch`
- **用途**: 批量交易指标（EigenPhi + Dune + RPC）
- **限制**: 最多 10 个交易哈希

## 2. 调用方式

### 2.1 请求

```json
{
  "tx_hashes": [
    "0x24c756ce474adba064012854a9c4bc6bfac6d5046b4aed5142500950162e9a2f",
    "0x88f0faf0a8a2874b10f2acedff874e92eb0e7ea30195b6cccbb4bedb02618d68",
    "0x49f3b1c7e52cf18e7a3464cf1b4b4ab8862a8d0c440b333bec4d7bdae03916da"
  ]
}
```

### 2.2 curl 示例

```bash
curl -s https://calltracesniffer-production.up.railway.app/api/tx-metrics-batch \
  -H "Content-Type: application/json" \
  -d '{"tx_hashes":["0x24c7...","0x88f0...","0x49f3..."]}'
```

## 3. 响应结构

```json
{
  "success": true,
  "block_start": 24182471,
  "block_end": 24278160,
  "results": [
    {
      "tx_hash": "0x...",
      "success": true,
      "blockNumber": 24278160,
      "gasUsed": 163062,
      "builderTip": "0.0000000261469917",
      "builderTipPerGas": "0.00000000000016035",
      "coinbaseTransfer": "0",
      "builderTipWithCT": "0.0000000261469917",
      "blockIndex": 326,
      "botAddress": "0x...",
      "builder": {
        "address": "0x...",
        "name": "BuilderNet"
      },
      "revenueEth": "0.000041305729358517",
      "revenueUsd": "0.12348122304454286404791789",
      "revenueUsdAll": "0.123481223044542864",
      "blockTxCount": 329
    }
  ]
}
```

失败时：

```json
{
  "success": false,
  "error": "错误信息"
}
```

## 4. 字段与来源

### 4.1 批次级字段

- `block_start` / `block_end`  
  - **来源**: EigenPhi `txMeta.blockNumber`  
  - **含义**: 本次 tx_hashes 的最小/最大区块号

### 4.2 交易级字段

- `tx_hash`  
  - **来源**: 请求输入
- `blockNumber`  
  - **来源**: EigenPhi `txMeta.blockNumber`
- `gasUsed`  
  - **来源**: EigenPhi `txMeta.gasUsed`
- `blockIndex`  
  - **来源**: EigenPhi `txMeta.transactionIndex`
- `botAddress`  
  - **来源**: EigenPhi `txMeta.transactionToAddress`（tx.to）
- `builder.address`  
  - **来源**: Dune `builder_address`  
  - **回退**: EigenPhi `txMeta.blockMiner`
- `builder.name`  
  - **来源**: Dune `builder`
- `blockTxCount`  
  - **来源**: RPC `eth_getBlockByNumber(blockNumber)` 的 `transactions.length`

### 4.3 费用与收益字段

**builderTipPerGas / builderTip**
- **来源**: EigenPhi `txMeta.gasPrice` + `txMeta.baseFeePerGas` + `txMeta.gasUsed`
- **公式**:
```
builderTipPerGas = max(0, gasPrice - baseFeePerGas)
builderTip = builderTipPerGas * gasUsed
```
- **回退**: 若 EigenPhi 缺少 gas 字段，则用 Dune `priority_fee` 推导 builderTip

**coinbaseTransfer / builderTipWithCT**
- `coinbaseTransfer`  
  - **来源**: Dune `miner_tip_amount`（为空按 0）
- `builderTipWithCT`  
  - **公式**: `builderTip + coinbaseTransfer`

**revenueEth / revenueUsd / revenueUsdAll**
- `revenueEth`  
  - **来源**: EigenPhi `tokenFlows`  
  - **口径**: 仅 ETH/WETH（`tokenSpec == PLATFORM` 或 `tokenAddress == WETH`）的 `tokenAmount` 之和 / 1e18
- `revenueUsd`  
  - **来源**: `revenueEth * ethPriceUsd`  
  - **ethPriceUsd**: EigenPhi `tokenPrices` 中 PLATFORM/WETH 价格
- `revenueUsdAll`  
  - **来源**: EigenPhi `tokenFlows` 中 bot 地址的所有 `tokenBalances.tokenVolume` 之和

## 5. 单位与格式

- `builderTip*`, `coinbaseTransfer`, `revenueEth`: **ETH**（字符串）
- `builderTipPerGas`: **ETH/gas**（字符串）
- `revenueUsd*`: **USD**（字符串）
- `gasUsed`, `blockIndex`, `blockTxCount`: 整数

## 6. 数据源说明

- **EigenPhi**: `https://storage.googleapis.com/eigenphi-ethereum-tx/{tx_hash}`  
- **Dune Query**: `6569281`  
- **RPC**: 以太坊主网 JSON-RPC（用于区块交易数）
