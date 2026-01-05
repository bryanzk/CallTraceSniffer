OP IR Spec (Bilingual) / OP IR 规范（中英对照）
=============================================

Purpose / 目标
--------------
Define the target IR schema and parsing rules. The spec is self-contained and
does not require the reader to refer to any implementation document.

定义目标 IR 结构与解析规则。规范自解释，不依赖任何实现文档。

Top-Level Output / 顶层输出
--------------------------
An IR document is a JSON object with the following keys:
- tx_hash: string
- pattern: string (optional; currently empty in test cases)
- baseTokenAmountIn: number | null
- baseTokenAmountOut: number | null
- rootTrace: ExecutionNode

IR 文档是一个 JSON 对象，包含如下字段：
- tx_hash: string
- pattern: string（可选；测试用例中为空）
- baseTokenAmountIn: number | null
- baseTokenAmountOut: number | null
- rootTrace: ExecutionNode

ExecutionNode / 执行节点
------------------------
ExecutionNode is a tree node with the following ordering requirements:
- Swap node: keys order must be `type`, `swap`, `callback`, `transfer`
- Transfer node: keys order must be `type`, `transfer`, `swap`
- Remove empty keys (e.g., no `callback` when empty)

ExecutionNode 是树节点，字段顺序要求：
- Swap 节点：`type`, `swap`, `callback`, `transfer`
- Transfer 节点：`type`, `transfer`, `swap`
- 空字段不输出（例如没有 callback 时不输出）

ExecutionNode fields:
- type: "swap" | "transfer" | "unknown" | other
- swap: SwapData | null
- transfer: TransferData | null
- callback: ExecutionNode[] (optional)
- wethWrapOrUnwarp: null (present in test cases for swap nodes, can be omitted if not required)

ExecutionNode 字段：
- type: "swap" | "transfer" | "unknown" | other
- swap: SwapData | null
- transfer: TransferData | null
- callback: ExecutionNode[]（可选）
- wethWrapOrUnwarp: null（测试用例里出现，可按需输出）

SwapData / 交换数据
------------------
SwapData contains:
- swapIntent: SwapIntent
- executionArgs: ExecutionArgs

SwapData 包含：
- swapIntent: SwapIntent
- executionArgs: ExecutionArgs

SwapIntent fields:
- poolId: string
- protocolId: 2 | 3 | 4
- tokenIn: string (lowercase address)
- tokenOut: string (lowercase address)
- tokenInDecimals: number | null (appears in test cases for some txs)
- tokenOutDecimals: number | null (appears in test cases for some txs)
- amountInBig: string | number
- amountOutBig: string | number

SwapIntent 字段：
- poolId: string
- protocolId: 2 | 3 | 4
- tokenIn: string（小写地址）
- tokenOut: string（小写地址）
- tokenInDecimals: number | null（测试用例中部分有值）
- tokenOutDecimals: number | null（测试用例中部分有值）
- amountInBig: string | number
- amountOutBig: string | number

ExecutionArgs fields:
- amount: string | null
- isAmountIn: boolean
- zeroForOne: boolean
- recipient: string
- recipientIsBot: boolean
- recipientType: number
- tokenInIsWETH: boolean
- tokenOutIsWETH: boolean

ExecutionArgs 字段：
- amount: string | null
- isAmountIn: boolean
- zeroForOne: boolean
- recipient: string
- recipientIsBot: boolean
- recipientType: number
- tokenInIsWETH: boolean
- tokenOutIsWETH: boolean

TransferData / 转账数据
-----------------------
TransferData fields:
- tokenId: string (token contract address, lowercase)
- to: string (recipient address)
- amount: string | number

TransferData 字段：
- tokenId: string（token 合约地址，小写）
- to: string（收款地址）
- amount: string | number

Field Mapping: BlockSec vs Tenderly / 字段映射：BlockSec 与 Tenderly
-------------------------------------------------------------------
- tx_hash:
  - BlockSec: trace_data.tx_hash (fallback to provided tx hash)
  - Tenderly: external tx hash or trace root
- tx_hash:
  - BlockSec: trace_data.tx_hash（若缺失则使用传入的 tx_hash）
  - Tenderly: 外部传入的 tx_hash 或 trace 根节点

- rootTrace (tree):
  - BlockSec: build from mainTrace + dataMap (call tree)
  - Tenderly: build from flat traceAddress lexicographic tree
- rootTrace（树）:
  - BlockSec: 由 mainTrace + dataMap 构建调用树
  - Tenderly: 由 traceAddress 词典序构建树

- swapIntent.poolId:
  - BlockSec:
    - V4: poolManagerAddress|poolId topic (from Swap log)
    - V3/V2: pool contract address (invocation.address)
  - Tenderly: apply the same protocol detection principles defined here
- swapIntent.poolId:
  - BlockSec:
    - V4: poolManagerAddress|poolId topic（来自 Swap log）
    - V3/V2: pool 合约地址（invocation.address）
  - Tenderly: 按本规范的协议识别规则处理

- swapIntent.protocolId:
  - BlockSec: detect via logs (topics) or known signatures; V4 > V3 > V2
  - Tenderly: apply the same poolId rules defined here
- swapIntent.protocolId:
  - BlockSec: 通过 logs/topics 或签名识别；优先级 V4 > V3 > V2
  - Tenderly: 按本规范的 poolId/协议识别规则处理

- swapIntent.tokenIn/tokenOut:
  - BlockSec: from decoded callParams (V4 key/params), logs heuristic otherwise
  - Tenderly: from decoded input + transfer-log heuristics defined here
- swapIntent.tokenIn/tokenOut:
  - BlockSec: V4 从 decoded callParams（key/params）提取，否则用 logs 推断
  - Tenderly: 从 decoded input + transfer log 规则推断

- swapIntent.amountInBig/amountOutBig:
  - BlockSec:
    - V3: from returnParams amount0/amount1 with zeroForOne
    - V2: from Swap log data
    - V4: from swapDelta or log fields
  - Tenderly: same token/amount rules defined here
- swapIntent.amountInBig/amountOutBig:
  - BlockSec:
    - V3: 由 returnParams amount0/amount1 + zeroForOne 计算
    - V2: 由 Swap log data 计算
    - V4: 由 swapDelta 或日志字段计算
  - Tenderly: 按本规范的 token/amount 规则处理

- executionArgs.recipient:
  - BlockSec: decoded callParams (recipient/to) or log
  - Tenderly: decoded input params
- executionArgs.recipient:
  - BlockSec: decoded callParams（recipient/to）或日志
  - Tenderly: decoded input 参数

- transfer.tokenId/to/amount:
  - BlockSec: invocation.address + decoded callParams
  - Tenderly: t.to + decoded input params
- transfer.tokenId/to/amount:
  - BlockSec: invocation.address + decoded callParams
  - Tenderly: t.to + decoded input 参数

Tenderly Parsing Rules / Tenderly 解析规则
----------------------------------------
Input data:
- traces: flat trace list with `traceAddress` and decoded inputs/outputs
- logs: event logs list

输入数据：
- traces：扁平化 trace 列表（含 `traceAddress` 与 decoded input/output）
- logs：事件日志列表

Node selection:
- Only CALL traces are considered.
- If method == swap (or known swap sig), classify as swap.
- If method == transfer and `from == tx.to`, classify as transfer.
- All other calls are ignored.

节点筛选：
- 仅处理 CALL 类型的 trace。
- method == swap（或已知 swap 签名）判定为 swap。
- method == transfer 且 `from == tx.to` 判定为 transfer。
- 其他调用忽略。

Tree reconstruction:
- Use lexicographical sort on traceAddress.
- Parent is the longest prefix traceAddress of a node.
- Build a single tree (use first root node as rootTrace).

树重建：
- 按 traceAddress 词典序排序。
- 父节点为 traceAddress 的最长前缀。
- 构建单棵树（取第一个 root 作为 rootTrace）。

Protocol detection (swap):
- Use log topics to detect V4/V3/V2:
  - V4: TOPIC_V4 or PoolManager address (0x000000000004444c5dc75cb358380d2e3de08a90)
  - V3: TOPIC_V3 or sig 0x128acb08
  - V2: TOPIC_V2 or sig 0x022c0d9f
  - Priority: V4 > V3 > V2

协议识别（swap）：
- 通过日志 topic 识别 V4/V3/V2：
  - V4：TOPIC_V4 或 PoolManager 地址 (0x000000000004444c5dc75cb358380d2e3de08a90)
  - V3：TOPIC_V3 或签名 0x128acb08
  - V2：TOPIC_V2 或签名 0x022c0d9f
  - 优先级：V4 > V3 > V2

Swap extraction by protocol:
- V4:
  - poolId = "<poolManagerAddress>|<poolIdTopic>" when log topic present
  - tokenIn/tokenOut from key.currency0/1 and params.zeroForOne
  - amountInBig from swapDelta output (if present)
- V3:
  - poolId = pool address
  - tokenIn/tokenOut inferred from transfer logs touching pool (heuristic)
  - amountInBig/amountOutBig from decoded output amount0/amount1 and zeroForOne
- V2:
  - tokenIn/tokenOut inferred from transfer logs touching pool (heuristic)
  - amountInBig/amountOutBig from Swap log data

按协议抽取 swap：
- V4：
  - log topic 存在时 poolId = "<poolManagerAddress>|<poolIdTopic>"
  - tokenIn/tokenOut 来自 key.currency0/1 与 params.zeroForOne
  - amountInBig 来自 swapDelta 输出（如有）
- V3：
  - poolId = pool 地址
  - tokenIn/tokenOut 通过与 pool 相关的 Transfer log 推断（启发式）
  - amountInBig/amountOutBig 来自 decoded output amount0/amount1 + zeroForOne
- V2：
  - tokenIn/tokenOut 通过与 pool 相关的 Transfer log 推断（启发式）
  - amountInBig/amountOutBig 来自 Swap log data

BlockSec Mapping (target behavior) / BlockSec 映射目标
-----------------------------------------------------
Use BlockSec trace_data:
- dataMap + mainTrace for call tree
- invocation.decodedMethod, callParams, returnParams for swap/transfer
- event logs for protocol detection (if available)

Target alignment:
- Produce the same ExecutionNode schema across data sources.
- Use the same protocol detection and token inference principles defined here.
- Emit JSON output for comparisons and test case validation.

使用 BlockSec trace_data：
- dataMap + mainTrace 构建调用树
- invocation.decodedMethod、callParams、returnParams 提取 swap/transfer
- event logs 用于协议识别（若可用）

对齐目标：
- 各数据源输出一致的 ExecutionNode 结构
- 使用本规范的协议识别与 token 推断规则
- 输出 JSON 以便对比与测试用例验证

Notes / 备注
------------
- tokenInDecimals/tokenOutDecimals sources are TBD. If unavailable, set null
  unless test cases require fixed values for specific cases.
- `wethWrapOrUnwarp` appears in test cases but is null; may be omitted unless required.

备注：
- tokenInDecimals/tokenOutDecimals 来源待定；不可用时设为 null，除非测试用例要求固定值。
- `wethWrapOrUnwarp` 在测试用例中为 null，可按需省略。
