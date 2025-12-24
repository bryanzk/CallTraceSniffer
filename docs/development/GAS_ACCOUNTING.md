OP IR Gas Accounting / OP IR Gas 记账规范
========================================

Purpose / 目标
--------------
Define how gasUsed from BlockSec traces should map into OP IR outputs, and where
to present scope-level gas so the results are consistent and non-duplicative.

定义 BlockSec trace 中的 gasUsed 如何映射到 OP IR 输出，并给出 scope 级别
gas 的展示位置，确保结果一致且不重复计数。

Core Principles / 核心原则
-------------------------
1. Real gas comes only from on-chain invocations in BlockSec traces.
2. OP2 "virtual/supplemental" edges are semantic links, not real execution.
3. Any gas derived from OP2 edges must not be double-counted.

1. 真实 gas 只来自 BlockSec trace 里的真实调用。
2. OP2 的“虚拟/补边”只是语义关系，不是实际执行。
3. 任何来自 OP2 的 gas 不应被重复计入。

Mapping Rules / 映射规则
------------------------
1. Transfer edges that come from trace invocations:
   - gasUsed := invocation.gasUsed
   - gasCost := gasUsed (no extra conversion)

1. 由 trace invocation 产生的 transfer 边：
   - gasUsed := invocation.gasUsed
   - gasCost := gasUsed（不做额外换算）

2. OP2 virtual/supplemental edges:
   - gasUsed := None (or 0 if a numeric value is required)
   - gasCost := same as gasUsed
   - These edges are excluded from total gas and scope gas summaries.

2. OP2 虚拟/补边：
   - gasUsed := None（如必须数值可用 0）
   - gasCost := 同 gasUsed
   - 不参与 total gas 与 scope gas 统计

3. Swap scope gas:
   - For each Scope swap, sum gasUsed of all invocations in its trace subtree.
   - This includes nested calls such as PoolManager.swap, sync, settle, take,
     transferFrom, etc.
   - This produces a "scope_gas_used" that reflects real cost of the swap.

3. Swap scope gas：
   - 对每个 Scope swap，汇总其 trace 子树所有 invocation 的 gasUsed。
   - 包含 PoolManager.swap 及其内部的 sync/settle/take/transferFrom 等调用。
   - 该汇总得到的 scope_gas_used 代表 swap 的真实成本。

Output Placement Recommendation / 输出位置建议
---------------------------------------------
Show scope gas in the Swaps section per swap line:
  [0] 0x.... | Form: Scope | GasUsed: 76,482 | Plan: ...

在 Swaps 列表的每一行展示 scope gas：
  [0] 0x.... | Form: Scope | GasUsed: 76,482 | Plan: ...

Rationale / 原因
---------------
- The cost belongs to the swap itself, not the tree structure.
- Keeps the total gas summary intact and avoids mixing with virtual edges.

- 成本属于 swap 本身，而非树结构。
- 保持 total gas 统计清晰，避免与虚拟边混淆。

Example (Uni V4 unlock path) / 示例（Uni V4 unlock 路径）
-------------------------------------------------------
For a trace sequence:
  UniversalRouter.execute
    -> PoolManager.unlock
       -> unlockCallback
          -> PoolManager.swap
             -> sync / settle / take / transferFrom

对于以下 trace 序列：
  UniversalRouter.execute
    -> PoolManager.unlock
       -> unlockCallback
          -> PoolManager.swap
             -> sync / settle / take / transferFrom

All gasUsed values above are real and should be summed into the swap scope gas.
Any OP2 virtual or supplemental edges created to represent logical flows must
remain gas-less (None/0) to avoid double counting.

以上调用的 gasUsed 都是实际消耗，应汇总进 swap scope gas。
为表达逻辑资金流而生成的 OP2 虚拟/补边应保持 gas-less（None/0），避免重复计数。

Decision Summary / 结论
-----------------------
- Keep BlockSec gasUsed as the only source of truth.
- Mark OP2 virtual/supplemental edges as gas-less.
- Attach scope_gas_used to Swaps lines for human-readable reporting.

- 仅以 BlockSec gasUsed 作为真实来源。
- OP2 虚拟/补边不计 gas。
- 将 scope_gas_used 放在 Swaps 行方便阅读。
