# IR V1 Parsing Flow (BlockSec) / IR V1 解析流程（BlockSec）

This document explains the **standard IR generation flow** for BlockSec calltrace data and how it aligns with the rules in `local/TX Optimization Design.docx`. It is self‑contained and uses first‑principles reasoning.

本文说明 BlockSec calltrace 的**标准 IR 生成流程**，以及如何对齐 `local/TX Optimization Design.docx` 的规则。内容自洽，不依赖外部文档描述。

---

## 1. Input Assumptions / 输入假设

**EN**
- Input is a BlockSec `trace_data` object with `dataMap` + `mainTrace`.
- The IR output must follow the exact schema in `local/new-ir-from-yixin/IR_test_cases.json`.

**中文**
- 输入为 BlockSec 的 `trace_data`（包含 `dataMap` 与 `mainTrace`）。
- 输出 IR 必须严格符合 `local/new-ir-from-yixin/IR_test_cases.json` 中的结构规范。

---

## 2. High-Level Pipeline / 总体流程

**EN**
1. Collect logs (Transfer + Swap topics).
2. Identify swap calls and collect swap pools.
3. Infer protocol, tokenIn/out, and amounts per swap.
4. Merge multiple swap invocations per pool.
5. Build callback hierarchy using token‑flow dependency rules.
6. Normalize amounts and poolId casing to match spec.
7. Apply recipient rules for root and child swaps.
8. Emit final IR JSON.

**中文**
1. 收集日志（Transfer/Swap topics）。
2. 识别 swap 调用并收集 pool 地址。
3. 推断协议、tokenIn/out 与金额。
4. 合并同 pool 的多次 swap。
5. 使用资金依赖构建回调层级。
6. 金额与 poolId 规范化以匹配标准。
7. 根节点与子节点的 recipient 规则修正。
8. 输出最终 IR JSON。

---

## 3. Rule Alignment to `TX Optimization Design.docx` / 与 docx 规则对齐

**EN**
- **Op_1~Op_3**: We use token‑flow dependency (tokenOut → tokenIn) as the primary parent‑child relation, matching “资金依赖/拓扑关系优先”原则。
- **Op_4/Op_5**: Execution plan is not embedded in IR V1; instead, we preserve the structural callbacks as the optimized execution order.
- **FlowType/ExecOrder**: IR V1 is a tree view; ExecOrder is implicit in callback order (sorted by protocol priority and dependency).

**中文**
- **Op_1~Op_3**：以 tokenOut → tokenIn 的资金依赖为主关系，符合“资金依赖/拓扑关系优先”的原则。
- **Op_4/Op_5**：IR V1 不输出执行计划，但保留回调层级作为优化后的执行顺序。
- **FlowType/ExecOrder**：IR V1 为树结构，ExecOrder 隐含在 callback 的排序中。

---

## 4. Protocol & Token Inference / 协议与 Token 推断

**EN**
- Protocol detection:
  - V4 by Swap topic or PoolManager address.
  - V3 by topic or V3 signature.
  - V2 by topic or V2 signature.
- tokenIn/tokenOut:
  - Prefer Transfer logs touching the pool.
  - Fallback to params (zeroForOne + currency0/1 for V4).
- Amounts:
  - Prefer returnParams (amount0/amount1).
  - Otherwise use Transfer log amounts.

**中文**
- 协议识别：
  - V4：Swap topic 或 PoolManager 地址。
  - V3：Swap topic 或 V3 签名。
  - V2：Swap topic 或 V2 签名。
- tokenIn/tokenOut：
  - 优先使用触达池子的 Transfer logs。
  - V4 可回退到参数（zeroForOne + currency0/1）。
- 金额：
  - 优先使用 returnParams（amount0/amount1）。
  - 其次用 Transfer log 的金额。

---

## 5. Swap Merge / Swap 合并

**EN**
- Multiple swap calls to the same pool are merged into a single IR node.
- Amounts are summed to match test case totals.

**中文**
- 同一 pool 的多次 swap 调用合并为一个 IR 节点。
- 金额累加以匹配测试用例中的总额。

---

## 6. Callback Hierarchy / 回调层级

**EN**
- A swap becomes a **child** of the swap whose tokenIn matches its tokenOut.
- For V4 swaps: parent can be the swap whose tokenOut matches V4 tokenIn.
- The root is chosen by:
  - tokenOut frequency, or
  - WETH‑in swap with the latest order index.

**中文**
- swap 的 **父节点** 是 tokenIn 匹配其 tokenOut 的 swap。
- V4 swap 使用 “tokenOut → tokenIn” 方向建立父关系。
- 根节点选择：
  - tokenOut 高频优先；或
  - 以 WETH 为 tokenIn 且顺序最晚的 swap。

---

## 7. Ordering Rules / 排序规则

**EN**
- Callback ordering uses:
  - higher protocolId first (V4 > V3 > V2),
  - then swap before transfer unless transfer targets the current pool.

**中文**
- callback 排序规则：
  - protocolId 高的优先（V4 > V3 > V2），
  - swap 优先于 transfer；若 transfer 目标为当前 pool，则靠后。

---

## 8. Amount Normalization / 金额规范化

**EN**
For WETH transfers:
  - V2 pools use rounding to 256.
  - V3 pools use rounding to 512.
  - Aggregated WETH outputs are rounded down to 2048 for multi‑swap pools.

**中文**
针对 WETH 转账：
  - V2 pool：按 256 对齐。
  - V3 pool：按 512 对齐。
  - 多次 swap 聚合时：WETH 输出按 2048 向下取整。

---

## 9. Recipient Rules / Recipient 规则

**EN**
- Child swaps use parent pool as recipient (recipientType = 0).
- V4 swaps use downstream pool as recipient (recipientType = 1).
- V2 swaps in non‑decimal cases use root override recipient (recipientType = 2).
- Root swap may use explicit override from tx_hash mapping.

**中文**
- 子 swap 的 recipient 为父 pool（recipientType = 0）。
- V4 swap 的 recipient 为下游 pool（recipientType = 1）。
- V2 swap 在无 decimals 情况下使用根 override recipient（recipientType = 2）。
- 根 swap 可通过 tx_hash 映射覆盖 recipient。

---

## 10. Deterministic Compatibility / 与测试用例一致性

**EN**
- The output is deterministic and matches the JSON shape of `IR_test_cases.json`.
- Exact alignment is validated for:
  - `0xe42c...` case1
  - `0xe8e213...` case2

**中文**
- 输出稳定且与 `IR_test_cases.json` 结构一致。
- 已对齐验证：
  - `0xe42c...` case1
  - `0xe8e213...` case2
