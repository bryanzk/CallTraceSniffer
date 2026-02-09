# 交易深度分析：0xa6af7632e1bdebc0dedb3a4ccbf8d08728ee7429b7b24740e96060f1a5a6b172

基于 EigenPhi `get_eigenphi_tx_mev`（include_raw）的完整解析。

---

## 一、交易概览

| 项目 | 值 |
|------|-----|
| **Tx Hash** | `0xa6af7632e1bdebc0dedb3a4ccbf8d08728ee7429b7b24740e96060f1a5a6b172` |
| **类型** | Arbitrage |
| **链** | Ethereum (Chain ID 1) |
| **区块** | 24329300 |
| **区块时间** | 1769554643 (UTC 时间戳) |
| **区块哈希** | 0xef596439da9a9d2d5e1ca9de13c849742400a22b108981d5d2f2a93846db9147 |
| **矿工** | 0x4838b106fce9647bdf1e7877bf73ce8b0bad5f97 |
| **Tx 在块内序号** | 7 |

### 1.1 主体与合约

| 角色 | 地址 | 说明 |
|------|------|------|
| **Arbitrageur (EOA)** | `0xc0ffeebabe5d496b2dde509f9fa189c25cf29671` | 套利机器人主控地址 |
| **Router / 执行合约** | `0xe08d97e151473a848c3d9ca3f323cb720472d015` | 实际执行多跳 swap 的合约 |
| **Miner** | `0x4838b106fce9647bdf1e7877bf73ce8b0bad5f97` | 区块矿工，收取 gas |

### 1.2 经济指标

| 指标 | 数值 (USD) |
|------|------------|
| **Profit** | 1.493545597133563568 |
| **Cost** | 0.279981724221379373 |
| **Revenue** | 1.773527321354942941 |
| **ROI** | profit/cost ≈ **5.33** |

### 1.3 Gas

| 项目 | 值 |
|------|-----|
| gasPrice | 45,672,364 wei (~45.67 Gwei) |
| baseFeePerGas | 45,672,364 wei |
| gasUsed | 831,858 |

Cost ≈ 0.28 USD 对应矿工实际收到的 ETH：约 93,181,548,225,782 wei（约 0.093 ETH × 时价 ≈ 0.28 USD）。

---

## 二、EigenPhi 汇总结构

- **tokenCount**: 7 种代币参与流转  
- **venueCount**: 3 个场所/池子  
- **types**: ["Arbitrage"]  
- **liquidationDetails**: []（无清算）

---

## 三、代币与场所（含地址与价格）

EigenPhi 在本次分析中使用的价格与缺价如下。

### 3.1 有价格的代币 (tokenPrices)

| 合约地址 | 说明 | 价格 (USD) |
|----------|------|-------------|
| 0xeeee...eeee | ETH (PLATFORM) | 3004.69062333 |
| 0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2 | WETH | 3004.69062333 |
| 0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48 | USDC | ~1（以内部换算为准） |
| 0x45804880de22913dafe09f4980848ece6ecbaf78 | PAX Gold (PAXG) | 5197.88 |
| 0xeb269732ab75a6fd61ea60b06fe994cd32a83549 | 某 ERC20 | 1.008044 |

### 3.2 缺价代币 (missingTokenPrices)

- `0x355c665e101b9da58704a8fddb5feef210ef20c0`
- `0x369dffbb1d8f49ecf63501e2d175742ae1bfdfc8`

上述二者未参与 EigenPhi 的 USD 汇总计算，仅出现在 tokenFlows 的数量与方向中。

---

## 四、资金流 (tokenFlows) 逻辑梳理

按 EigenPhi 的 `tokenFlows` 与 `tokenVolume`，可归纳为以下逻辑路径（金额为 USD 或原链上单位，以 EigenPhi 标注为准）。

### 4.1 套利者净得（总利润）

- **0xc0ffeebabe5d496b2dde509f9fa189c25cf29671**  
  - 净增：PLATFORM ETH 数量合 **1.493545009718611503** USD（即 Profit 来源）  
  - 另持极少 **0xeb269732...**，EigenPhi 折算约 0.000000587414952065 USD，可忽略  

即：套利者最终多以「多收 ETH」的形式实现约 **1.49 USD** 利润。

### 4.2 矿工（成本）

- **0x4838b106fce9647bdf1e7877bf73ce8b0bad5f97 (Miner)**  
  - 净增：PLATFORM ETH，合 **0.279981724221379373** USD  
  - 对应本笔的 **Cost**，即 gas 支出。

### 4.3 中间场所与代币流向

EigenPhi 的 tokenFlows 按地址列出各处的 token 增删。与「套利路径」相关的典型环节可概括为：

1. **0x369dffbb1d8f49ecf63501e2d175742ae1bfdfc8**  
   - 减仓自有 token（LP 或 vault 凭证，缺价）  
   - 用于从池子中取出流动性或赎回。

2. **0x7fdcdad3b4a67e00d9fd5f22f4fd89a5fa4f57ba**  
   - 收到 0x369dff... 的 token、**USDC**（约 68.82 USD 规模）、并转出 **0xeb269732...**（约 -69.68 USD 体积）  
   - 对应「用 LP/凭证换 USDC + 另一种代币」或类似 DEX 多跳中的一腿。

3. **0xef6317e783b22b2a2fc073e68260450236c20779**  
   - 大量 **0xeb269732...** 流入（约 +69.68 USD），**0x355c665e...** 流出  
   - 对应 0xeb26... 与 0x355c66...（缺价）之间的兑换或池子间搬运。

4. **0x355c665e101b9da58704a8fddb5feef210ef20c0**  
   - **PAXG (0x45804880...)** 流出（约 -70.79 USD），**0x355c665e...** 自身体系内流入  
   - 与下一环节构成「PAXG ↔ 稳定币/其他资产」的一环。

5. **0x5ae13baaef0620fdae1d355495dc51a17adb4082**  
   - **USDC** 流出（约 -70.61 USD），**PAXG** 流入（约 +70.79 USD）  
   - 典型「USDC → PAXG」的 DEX 兑换。

6. **0xe0554a476a092703abdb3ef35c80e0d76d32939f**  
   - **WETH** 减少（约 -1.773526733939990876 USD），**USDC** 增加（约 +1.787636222523286205 USD）  
   - 对应「WETH → USDC」的最后一环或中间一环，与「最终套利者收到 ETH」的路径一致（例如前面各跳整体呈现「USDC/其他稳定资产 → 最终换成 ETH 回 EOA」）。

7. **0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2 (WETH)**  
   - 与 PLATFORM ETH 的 wrap/unwrap 对应（减 PLATFORM、增 WETH 或反之），用于与 DEX 的 WETH 面额一致。

以上 3 个 venue、7 种 token 共同构成「多池、多代币」的套利路径；EigenPhi 的 **venueCount: 3** 与 **tokenCount: 7** 与这些环节一致。

---

## 五、totalRevenues / totalCosts / profitNet（EigenPhi 口径）

- **totalRevenues**  
  - Arbitrageur：PLATFORM ETH 合 **1.773527321354942941** USD；另 0xe08d97... 上有极少 0xeb26... 的 **0.000000587414952065** USD。  
  - 即「收入」≈ **1.773** USD，且几乎全部为 ETH。

- **totalCosts**  
  - Miner：PLATFORM ETH **-0.279981724221379373** USD（即成本 0.28 USD）。

- **profitNet**  
  - Arbitrageur：ETH **+1.493545009718611503** USD，及极少 0xeb26...  
  - 与 **Profit = Revenue − Cost** 一致：1.773 − 0.28 ≈ 1.49 USD。

---

## 六、策略与风险解读

### 6.1 策略定性

- **类型**：单笔、多池、多代币 **Arbitrage**。  
- **执行模式**：同一区块内、同一 bot（c0ffee…）的多笔套利之一；本笔为其中 **ROI 最高的一笔**（在先前 11 笔样本中 ROI ≈ 5.33）。  
- **路径特征**：  
  - 涉及 **LP/凭证 → USDC + 0xeb26...**、**0xeb26... ↔ 0x355c66...**、**PAXG ↔ USDC**、**WETH ↔ USDC** 等环节；  
  - 最终净收入为 ETH，成本为 gas（ETH 给矿工）；  
  - 缺价代币 0x355c66...、0x369dff... 未进入 EigenPhi 的 USD 汇总，但不影响「以 ETH 计价的净盈亏」结论。

### 6.2 主体与合约

- **EOA**：`0xc0ffeebabe5d496b2dde509f9fa189c25cf29671`，与同块内其余多笔高 ROI 套利为同一 bot。  
- **Router**：`0xe08d97e151473a848c3d9ca3f323cb720472d015`，负责多跳 swap 与路由。  
- **矿工**：`0x4838b106fce9647bdf1e7877bf73ce8b0bad5f97`，仅体现为 gas 成本接收方。

### 6.3 风险与限制

- **竞争**：同块、同矿工下，与其它套利与做市单竞争排序与执行价格；gas 设置会影响是否被包进块、以及实际成交价。  
- **缺价与口径**：0x355c66...、0x369dff... 无 EigenPhi 价格，若需「按所有代币逐项算 USD」，需自行取价或接受仅以 ETH 计净利。  
- **流动性与滑点**：多池、多跳对池深与滑点敏感；若某一跳实际成交差于预期，整体 ROI 会下降。

---

## 七、链接与扩展分析

- **EigenPhi PnL**  
  https://eigenphi.io/mev/ethereum/tx/0xa6af7632e1bdebc0dedb3a4ccbf8d08728ee7429b7b24740e96060f1a5a6b172  

- **Etherscan**  
  可查同一 tx hash 的 call trace、内部调用与 event，用于与上述 token 地址、合约一一对照。  

- **延伸**  
  - 对 0x369dff...、0x355c66...、0x7fdcdad...、0xef6317...、0x5ae13b...、0xe0554a... 在 Etherscan 上查合约与池子类型（Uniswap V2/V3、Curve、其它 AMM），可进一步写出「池 A → 池 B → 池 C」的明确路径名称；  
  - 若 EigenPhi 或其它数据源提供 `get_eigenphi_tx_mev_analysis` 的策略步骤文本，可把「关键动作顺序」补进本章「策略定性」一节的执行细节中。

---

**数据来源**：EigenPhi MCP `get_eigenphi_tx_mev`，参数 `include_raw: true`。  
**文档生成**：基于上述 raw 中的 txMeta、tokenFlows、tokenPrices、summary、totalRevenues / totalCosts / profitNet 整理。
