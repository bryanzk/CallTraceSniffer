# Call Trace To IR Mapping | Call Trace 到 IR 映射说明

This document explains how BlockSec invocation flow / call trace is transformed into the final IR (ExecutionGraph) through Op_1~Op_5.  
本文说明如何将 BlockSec 的 invocation flow / call trace 通过 Op_1~Op_5 转换为最终 IR（ExecutionGraph）。

## 1) Input Sources | 输入来源

BlockSec returns `trace_data` with two key parts:  
BlockSec 返回的 `trace_data` 包含两个核心部分：

- `dataMap`: per-node call metadata  
  `dataMap`：按节点编号索引的调用元数据  
  - `invocation.address` (callee contract)  
    `invocation.address`（被调用合约）  
  - `invocation.fromAddress` (caller)  
    `invocation.fromAddress`（调用者）  
  - `invocation.selector`, `decodedMethod`, `callData`  
    `invocation.selector`、`decodedMethod`、`callData`  
  - `invocation.gasUsed`  
    `invocation.gasUsed`
- `mainTrace`: a tree of call nodes, including node ids and parent/child nesting  
  `mainTrace`：调用树结构，包含节点 id 与父子嵌套关系

These two sources provide both "what was called" and "in what structure/order".  
这两部分同时提供“调用了什么”和“调用结构/顺序”。

## 2) Base Extraction (Swaps / Transfers) | 基础抽取（Swaps / Transfers）

### Transfers | 转账
We detect ERC20 transfers from `dataMap`:  
从 `dataMap` 中识别 ERC20 transfer 调用：

- selector `0xa9059cbb`, or  
  selector 为 `0xa9059cbb`，或  
- decoded method name contains `transfer` and is not an event.  
  decoded 方法名包含 `transfer` 且不是 event。

For each transfer we extract:  
每条 transfer 抽取以下字段：

- `from` = `invocation.fromAddress`  
- `to` = decoded params (`to`, `recipient`, etc.)  
- `token` = `invocation.address`  
- `amount` = decoded param value (fallback to `callData` parsing)  

This produces the raw on-chain transfer list (not yet optimized).  
得到的是原始链上转账列表（尚未优化）。

### Swaps | 交换
We detect swap calls in `dataMap`:  
在 `dataMap` 中识别 swap 调用：

- decoded method name contains `swap`, but not `callback`.  
  decoded 方法名包含 `swap` 且不含 `callback`。

For each swap node we capture:  
每个 swap 节点记录：

- `node_id`, `address`, `method`, `gasUsed`

Additionally, we use `mainTrace` to derive the execution order and depth.  
同时使用 `mainTrace` 推导执行顺序与层级深度。

## 3) Initial ExecutionGraph | 初始 ExecutionGraph

We build the initial IR structure:  
构建初始 IR 结构：

- **Nodes**: swap nodes with inferred token_in / token_out  
  **Nodes**：swap 节点（含 token_in / token_out 推断）  
- **Edges**: raw transfer edges  
  **Edges**：原始 transfer 边  
- **ExecOrder**: swap node order from `mainTrace` (preorder)  
  **ExecOrder**：由 `mainTrace` 先序遍历得到的执行顺序

Node type inference:  
节点类型推断：

- `CallbackV4`: signature `swap((address,address,uint24,int24,address),(bool,int256,uint160),bytes)`  
- `Callback`: signature `swap(address,bool,int256,uint160,bytes)` or swap with callback data  
- `Flash`: method name contains `flash`  
- otherwise `Standard`  

Token inference:  
Token 推断：

- For v4 swap: use `key.currency0/currency1` + `params.zeroForOne/amountSpecified`  
  v4 swap：使用 `key.currency0/currency1` 与 `params.zeroForOne/amountSpecified`  
- For standard swap: infer from related transfers  
  standard swap：从关联 transfer 反推

## 4) Op_1 Deterministic_Direct | 拓扑直连

Goal: collapse Router hops into a direct edge.  
目标：将 Router 中转合并为 Direct 边。

Pattern:  
模式：

```
A -> Router (Token X, Amount N)
Router -> B (Token X, Amount N)
```

Becomes:  
变为：

```
A -> B (Direct, Token X, Amount N)
```

## 5) Op_2 Virtual_Reduction | 虚拟规约

Goal: reduce internal transfers to virtual edges and add missing internal funding.  
目标：将内部转账降级为虚拟边，并补足内部资金流。

Key behaviors:  
关键行为：

1) **V4 Scope input**  
   **V4 Scope 输入**  
   - If token_in is WETH: add `Router -> Scope` transfer  
     若 token_in 为 WETH：补 `Router -> Scope` transfer  
   - Else: add `Scope -> Scope` virtual (internal ledger)  
     否则补 `Scope -> Scope` virtual（内部记账）  
   - If a direct input already exists, avoid adding virtual  
     若已有 direct 输入，则不再补 virtual

2) **Scope output to Node input**  
   **Scope 输出匹配 Node 输入**  
   - If `Scope.token_out == Node.token_in`, add `Scope -> Node` direct  
     若 `Scope.token_out == Node.token_in`，补 `Scope -> Node` direct

3) **Singleton direct -> virtual**  
   **Singleton direct 降级为 virtual**  
   - Same-scope direct edges become virtual (gas 0)  
     同结算域 direct 降级为 virtual（gas 归零）

## 6) Op_3 Mandatory_Scope | 形态标记

Assign node Form:  
设置节点 Form：

- `Callback / CallbackV4 / Flash` -> `Scope`  
- `Standard` -> `Node`

This converts protocol semantics into AST forms.  
这一步将协议语义映射为 AST 形态。

## 7) Payload Construction | Payload 构建

We build parent/child relations from edges:  
根据边关系建立父子结构：

- `A -> B (Direct)` means `B.payload += A`  
  `A -> B (Direct)` 表示 `B.payload += A`  
- If there is a single v4 scope, it becomes the root; others are attached if no parent exists.  
  若只有一个 v4 scope，则作为根；其余节点若无父节点则挂载到该根下。  
- Payload order follows `ExecOrder`.  
  Payload 顺序按 `ExecOrder` 排序。

This creates the execution tree structure.  
最终得到执行树结构。

## 8) Op_4 Primitive_Conversion | 原语展开

For each Scope node, create an execution plan:  
对每个 Scope 节点生成执行计划：

```
Preamble: OptimisticTransfer(token_out)
Body: Payload
Postamble: Repay(token_in)
```

## 9) Op_5 Engulfing | 吞噬修复

Simulate balances through ExecOrder:  
按 ExecOrder 模拟余额：

- If a node cannot afford its input token, find a suitable Scope and engulf it into the Scope payload.  
  若节点无法支付输入代币，则寻找合适 Scope 并将其吞入 Scope 的 payload。  
- Supports forward and backward engulfing.  
  支持前向与后向吞噬。

## 10) Final IR Output | 最终 IR 输出

The final IR includes:  
最终 IR 包含：

- Swaps list with Form and ExecutionPlan  
  Swaps 列表（含 Form 与 ExecutionPlan）  
- ExecutionTree (root nodes + payload tree)  
  ExecutionTree（根节点 + payload 树）  
- Transfers list (Router / Direct / Virtual)  
  Transfers 列表（Router / Direct / Virtual）

## Case 12 Graph (From `local/output/case12_blocksec_data.json`)  
## Case 12 图（来源 `local/output/case12_blocksec_data.json`）

```
ExecutionTree:
Root: 0xFA4A4c55... (Scope)
  └─ Payload[0]: 0xa0D9aB5A... (Scope)
       └─ Payload[0]: 0xDDd23787... (Node)

Transfers (non-gas fields):
1) 0xFA4A4c55...  -> Router        | Token: 0xC02aaA39... | Amount: 102367672167038976
2) Router        -> 0xDDd23787...  | Token: 0xC02aaA39... | Amount: 100999999961169920
3) 0xa0D9aB5A...  -> 0xFA4A4c55...  | Token: 0x44971ABF... | Amount: 1662639843918011695104
4) 0xDDd23787...  -> 0xa0D9aB5A...  | Token: 0xA9E8aCf0... | Amount: 1373810866148348002304
```
