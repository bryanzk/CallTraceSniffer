# MEV 高 ROI 交易深入分析报告

本报告针对 **profit/cost > 1** 的 11 笔 EigenPhi MEV 交易，基于 `get_eigenphi_tx_mev` 摘要做归纳与策略解读。

---

## 一、概览与指标汇总

| # | tx_hash (缩写) | 类型 | Profit (USD) | Cost (USD) | ROI | Block | TxIdx | GasUsed |
|---|----------------|------|---------------|------------|-----|-------|-------|---------|
| 1 | 0xa6af7632…a6b172 | Arbitrage | 1.49 | 0.28 | **5.33** | 24329300 | 7 | 831858 |
| 2 | 0xdcce98e2…69fc4 | Arbitrage | 1.30 | 0.26 | **5.09** | 24329300 | 8 | 809980 |
| 3 | 0x48779f9a…c4117 | Arbitrage | 1.10 | 0.23 | **4.71** | 24329300 | 9 | 809980 |
| 4 | 0x5cbb403c…24068 | Arbitrage | 0.89 | 0.21 | **4.25** | 24329300 | 10 | 809980 |
| 5 | 0x6301d243…6829f | **Sandwich** | 1.76 | 0.46 | **3.79** | 24329304 | 0 | 85890 |
| 6 | 0x4637ccec…6155c | Arbitrage | 0.69 | 0.19 | **3.68** | 24329300 | 11 | 809980 |
| 7 | 0x7cfa14f6…59551 | Arbitrage | 1.77 | 0.49 | **3.58** | 24329297 | 190 | 287267 |
| 8 | 0x6adf9f8c…c6c31 | **Sandwich** | 2.34 | 0.66 | **3.54** | 24329292 | 0 | 503945 |
| 9 | 0x0d708b54…bccd6 | Arbitrage | 0.49 | 0.17 | **2.95** | 24329300 | 12 | 809980 |
| 10 | 0x65c189d8…58255 | Arbitrage | 0.28 | 0.14 | **1.98** | 24329300 | 13 | 809980 |
| 11 | 0x2456cc73…61a8 | Arbitrage | 0.28 | 0.16 | **1.78** | 24329298 | 39 | 369956 |

- **策略分布**：9 笔 **Arbitrage**，2 笔 **Sandwich**。
- **ROI 区间**：1.78～5.33；ROI > 4 的均为套利，且多出自同一区块、同一 bot。
- **成本区间**：约 0.14～0.66 USD；Sandwich 单笔成本、利润更高。

---

## 二、主体与区块聚类

### 2.1 套利 Bot：`0xc0ffeebabe5d496b2dde509f9fa189c25cf29671`

- **Router/执行合约**：`0xe08d97e151473a848c3d9ca3f323cb720472d015`
- **区块**：24329300（同一区块内连续多笔）
- **交易序号**：TxIdx 7～13，共 **7 笔**（即上表 #1、#2、#3、#4、#6、#9、#10）。
- **Gas**：单笔约 809980～831858，属高 gas、多笔连续执行。
- **矿工**：`0x4838b106fce9647bdf1e7877bf73ce8b0bad5f97`

**解读**：同一 bot 在同一块内密集发 7 笔套利，ROI 1.98～5.33，说明该块内存在多个可独立捕获的价差机会；策略偏「同一块内多机会、高 gas 抢优先序」。

### 2.2 Sandwich Bot：`0xae2fc483527b8ef99eb5d9b44875f005ba1fae13`

- **执行合约**：`0x1f2f10d1c40777ae1da742455c65828ff36df387`
- **涉及交易**：表 #5（Block 24329304）、#8（Block 24329292）。
- **类型**：均为 **Sandwich**，角色 **VirtualTotal (Virtual Total)**，即整笔三明治的汇总视角。
- **Gas**：85890（#5）、503945（#8）；#8 路径更长、成本与利润更高。

**解读**：同一 sandwich 主体在不同块做三明治，单笔利润 1.76～2.34 USD，成本 0.46～0.66 USD，ROI 约 3.5～3.8；策略为「跨块、选高价值 victim 的三明治」。

### 2.3 其他套利主体

- **#7**：`0xa1de68d07945b1ff1222a73418fa295cf02ed102` → `0x6745024462abf2c049f54b381c4ad4a8c8d999c4`，Block 24329297，TxIdx 190，Gas 287267。
- **#11**：`0x6e2c8549ecc8615f14351889066a4ef196a688cd` → `0xaf682de1f2e6f710731121a05a44cb3c1b511f7d`，Block 24329298，TxIdx 39，Gas 369956。

二者为独立套利，ROI 分别约 3.58、1.78，成本与利润规模中等。

---

## 三、策略与风险收益特征

### 3.1 套利（Arbitrage）

- **来源**：DEX/CEX 或跨池价差、同块内多路径套利。
- **样本特点**：
  - 高 ROI（>4）集中在 **c0ffee…** 的 7 笔：成本 0.14～0.28 USD，单笔利润 0.28～1.49 USD。
  - 单笔成本与 gas 强相关；同一 router、同一块内多笔，说明路由/路径已模板化，通过提高 gas 争抢同一块内多个机会。
- **风险**：与同一块内其它套利者、造市商竞争；若 gas 估错或滑点变大，容易单笔或整块收益下降。

### 3.2 三明治（Sandwich）

- **来源**：在 victim 交易前后各下一笔，通过 victim 的滑点获利。
- **样本特点**：
  - 2 笔均为 **VirtualTotal**，即多笔子交易合并为一条「虚拟总交易」统计。
  - 单笔利润、成本均高于多数套利样本（利润 1.76～2.34，成本 0.46～0.66），ROI 约 3.5～3.8。
  - Gas 差异大（85k vs 503k），反映策略复杂度或路径长度差异。
- **风险**：依赖对 victim 的识别与排队；需在相同或相邻块内完成前后两笔，对区块构建与排序更敏感。

### 3.3 区块与时间集中度

- **区块范围**：24329292～24329304（约 12 个块）。
- **同一块 24329300**：出现 7 笔高 ROI 套利（c0ffee…），说明该块内流动性或订单流出现了多轮可套利价差。
- **矿工**：`0x4838b106fce9647bdf1e7877bf73ce8b0bad5f97`、`0x396343362be2a4da1ce0c1c210945346fb82aa49` 各覆盖部分交易，说明高 ROI 不绑定单一 builder，更多取决于链上机会与 bot 策略。

---

## 四、逐笔摘要与链接

以下保留每笔的 EigenPhi 摘要要点与 PnL 链接，便于按需查阅或做后续链上/策略分析。

### 交易 1 | ROI 5.33 | Arbitrage

- **Tx**: [0xa6af7632e1bdebc0dedb3a4ccbf8d08728ee7429b7b24740e96060f1a5a6b172](https://eigenphi.io/mev/ethereum/tx/0xa6af7632e1bdebc0dedb3a4ccbf8d08728ee7429b7b24740e96060f1a5a6b172)
- Profit 1.49 / Cost 0.28 / Revenue 1.77 USD
- Block 24329300, TxIdx 7, From c0ffee…, To e08d97…, GasUsed 831858

### 交易 2 | ROI 5.09 | Arbitrage

- **Tx**: [0xdcce98e215122eb9cb4204729c51bafed667841d34087cde4db9822deb769fc4](https://eigenphi.io/mev/ethereum/tx/0xdcce98e215122eb9cb4204729c51bafed667841d34087cde4db9822deb769fc4)
- Profit 1.30 / Cost 0.26 / Revenue 1.55 USD
- Block 24329300, TxIdx 8, From c0ffee…, To e08d97…, GasUsed 809980

### 交易 3 | ROI 4.71 | Arbitrage

- **Tx**: [0x48779f9a9bc6800db8b47bfa5feda4d7dab32545bf18b653ab2d9018fbcc4117](https://eigenphi.io/mev/ethereum/tx/0x48779f9a9bc6800db8b47bfa5feda4d7dab32545bf18b653ab2d9018fbcc4117)
- Profit 1.10 / Cost 0.23 / Revenue 1.33 USD
- Block 24329300, TxIdx 9, From c0ffee…, To e08d97…, GasUsed 809980

### 交易 4 | ROI 4.25 | Arbitrage

- **Tx**: [0x5cbb403ce0e905e2f987b19b3a2bc091a12544564684d597b7c987be0d124068](https://eigenphi.io/mev/ethereum/tx/0x5cbb403ce0e905e2f987b19b3a2bc091a12544564684d597b7c987be0d124068)
- Profit 0.89 / Cost 0.21 / Revenue 1.10 USD
- Block 24329300, TxIdx 10, From c0ffee…, To e08d97…, GasUsed 809980

### 交易 5 | ROI 3.79 | Sandwich (VirtualTotal)

- **Tx**: [0x6301d2438d2228677ec92f5ef97af1bff91282fdaa3c8d03722fced9cf76829f](https://eigenphi.io/mev/ethereum/tx/0x6301d2438d2228677ec92f5ef97af1bff91282fdaa3c8d03722fced9cf76829f)
- Profit 1.76 / Cost 0.46 / Revenue 2.22 USD
- Block 24329304, TxIdx 0, From ae2fc4…, To 1f2f10…, GasUsed 85890

### 交易 6 | ROI 3.68 | Arbitrage

- **Tx**: [0x4637cceca4e7ea0861cfd99d6135d9ae73aceadc43df1519d18bbb4203e6155c](https://eigenphi.io/mev/ethereum/tx/0x4637cceca4e7ea0861cfd99d6135d9ae73aceadc43df1519d18bbb4203e6155c)
- Profit 0.69 / Cost 0.19 / Revenue 0.88 USD
- Block 24329300, TxIdx 11, From c0ffee…, To e08d97…, GasUsed 809980

### 交易 7 | ROI 3.58 | Arbitrage

- **Tx**: [0x7cfa14f663c8ea808e8bd94b3f3f1f2fbf7a570887a8c3e4a1d89e7fad259551](https://eigenphi.io/mev/ethereum/tx/0x7cfa14f663c8ea808e8bd94b3f3f1f2fbf7a570887a8c3e4a1d89e7fad259551)
- Profit 1.77 / Cost 0.49 / Revenue 2.27 USD
- Block 24329297, TxIdx 190, From a1de68…, To 674502…, GasUsed 287267

### 交易 8 | ROI 3.54 | Sandwich (VirtualTotal)

- **Tx**: [0x6adf9f8ce1b32995ad7d325b4a9161293cb6f48357100752f2d929c730ec6c31](https://eigenphi.io/mev/ethereum/tx/0x6adf9f8ce1b32995ad7d325b4a9161293cb6f48357100752f2d929c730ec6c31)
- Profit 2.34 / Cost 0.66 / Revenue 3.00 USD
- Block 24329292, TxIdx 0, From ae2fc4…, To 1f2f10…, GasUsed 503945

### 交易 9 | ROI 2.95 | Arbitrage

- **Tx**: [0x0d708b54fc842d4a5999d47050eaa676dcd3f55cd21625e05a7bbb4ea6ebccd6](https://eigenphi.io/mev/ethereum/tx/0x0d708b54fc842d4a5999d47050eaa676dcd3f55cd21625e05a7bbb4ea6ebccd6)
- Profit 0.49 / Cost 0.17 / Revenue 0.65 USD
- Block 24329300, TxIdx 12, From c0ffee…, To e08d97…, GasUsed 809980

### 交易 10 | ROI 1.98 | Arbitrage

- **Tx**: [0x65c189d87112ca4df2c1bab40bdf6a68a7ae34ea6d1c2a6d9a3f768819f58255](https://eigenphi.io/mev/ethereum/tx/0x65c189d87112ca4df2c1bab40bdf6a68a7ae34ea6d1c2a6d9a3f768819f58255)
- Profit 0.28 / Cost 0.14 / Revenue 0.43 USD
- Block 24329300, TxIdx 13, From c0ffee…, To e08d97…, GasUsed 809980

### 交易 11 | ROI 1.78 | Arbitrage

- **Tx**: [0x2456cc733c4137d5751ed043ccb7b409925602fd11028cb7f9eabc44ca9c61a8](https://eigenphi.io/mev/ethereum/tx/0x2456cc733c4137d5751ed043ccb7b409925602fd11028cb7f9eabc44ca9c61a8)
- Profit 0.28 / Cost 0.16 / Revenue 0.43 USD
- Block 24329298, TxIdx 39, From 6e2c85…, To af682d…, GasUsed 369956

---

## 五、结论与可延伸方向

1. **高 ROI 集中度**：ROI > 4 的 4 笔均来自同一套利 bot（c0ffee…）在同一块（24329300）内的多笔执行，说明「单块多机会 + 高 gas 抢位」是当前样本中 ROI 最高的模式。
2. **策略分化**：套利以「低成本、多笔、同块」为主；三明治以「单笔利润与成本更高、VirtualTotal 汇总」为主，ROI 约 3.5～3.8。
3. **成本与 Gas**：Cost 与 GasUsed 正相关；同一 router 下 gas 模板化（如 809980）利于复用到多笔类似路径。
4. **可延伸分析**：  
   - 用 `get_eigenphi_tx_mev_analysis` 或 EigenPhi 前端逐笔查看路径与代币流；  
   - 按 router、区块、矿工做时间序列或相关性分析；  
   - 结合 Dune/区块浏览器，看同一块内 victim 与套利/sandwich 的先后关系与流动性来源。

数据来源：EigenPhi MCP `get_eigenphi_tx_mev`，链上区块 24329292～24329304 窗口内、profit/cost > 1 的 11 笔 MEV 交易。
