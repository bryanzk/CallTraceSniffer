# CallTraceSniffer 能力地图与仓库边界（MEV / EigenPhi / BlockSec）

> 更新日期：2026-02-09  
> 目的：把“线上服务（Online Service）”与“研究工具（Research Toolkit）”的能力、输入输出、依赖与产物边界讲清楚，避免主干被生成物/笔记污染，同时保留可复现的研究链路。

---

## 1. 产品形态（两条线并行，但边界要清晰）

### 形态 A：在线服务（Online Service，面向部署/对外 API）

**目标**：对外提供稳定 API 与 Web UI，支持：
- BlockSec：`tx_hash / simulation_url -> trace_data -> IR V1 -> Mermaid`
- MEV 区块 Viewer：`block_number -> HTML + SVG 资源浏览`

**关键约束**：
- 依赖必须可在 Docker 中稳定安装（系统依赖、Python 依赖明确）
- 不把“分析笔记/一次性脚本输出”当作线上必需文件
- 大体量生成物要么外置（对象存储/缓存），要么只保留少量样例

### 形态 B：研究工具（Research Toolkit，面向分析/复现/报告）

**目标**：快速迭代、可复现实验、沉淀研究结论：
- 通过 MCP WebSocket 拉 EigenPhi 最新 MEV / 实时流
- 过滤 ROI，批量拉策略分析文本，生成报告
- 从 EigenPhi analyseTransaction 生成 Token Flow 图（Mermaid/DOT/SVG/HTML）
- PnL 异常溯源与价格交叉验证（CMC/CoinGecko/其他源）

**关键约束**：
- 允许“可选依赖”（例如 `websockets`、Graphviz 系统 `dot`）
- 产物默认写到 `outputs/` 或本地文件，避免污染仓库
- 研究笔记是否入库由团队约定（建议有“索引/目录”，否则会噪）

---

## 2. 能力地图（输入 / 输出 / 依赖 / MCP 工具）

### 2.1 在线服务：API 与 Web 路由

| 能力 | 入口 | 输入 | 输出 | 关键依赖 | 外部依赖 |
|---|---|---|---|---|---|
| 单笔 tx 分析 | `POST /api/analyze`（`/Users/kezheng/Codes/CursorDeveloper/CallTraceSniffer/src/calltrace/api/routes.py`） | `tx_hash` | `trace_data`（缓存）、`ir_v1`、`ir_v1_json`、`stats`、`mermaid_dag` | `BlockSecExtractor`（Playwright 抓取）、`build_blocksec_ir` | BlockSec 页面/API（通过浏览器网络响应获取） |
| simulation 分析 | `POST /api/analyze-simulation` | `simulation_url` | 同上 | `BlockSecExtractor.parse_simulation_url` + Playwright | BlockSec |
| 批量分析 | `POST /api/analyze-batch`、`POST /api/analyze-simulation-batch` | `tx_hashes` / `simulation_urls` | 批量结果 | 同上 | BlockSec |
| IR 导出 | `POST /api/ir_parse` | `tx_hash` | `application/json`（IR V1） | 缓存命中直接返回，否则抓取+解析 | BlockSec |
| IR -> Mermaid | `POST /api/ir-to-mermaid` | `ir_v1` | `mermaid_dag` | `build_mermaid_dag` | 无 |
| MEV 区块 HTML 片段生成 | `POST /api/mev/block` | `block_number` | 可嵌入 HTML 片段（并产出/引用 SVG） | `MevBlockService` | MCP EigenPhi Server、RPC（视服务实现） |
| MEV 区块 Viewer | `GET /mev/block/<block_number>` | path param | `token_flow_graphs/block_<n>/index.html` | 静态文件存在性检查 | 文件系统（`token_flow_graphs/`） |
| MEV Viewer 资源 | `GET /mev/block/<block_number>/<filename>` | path param | SVG 等资源文件 | 目录/文件安全检查 | 文件系统 |

备注：
- MEV Viewer 的部署与产物结构见：`/Users/kezheng/Codes/CursorDeveloper/CallTraceSniffer/docs/deployment/MEV_BLOCK_VIEWER.md`
- 在线服务的“强依赖”应尽量固定在 `requirements.txt` + Dockerfile 的系统依赖中，避免运行期再装。

### 2.2 研究工具：脚本与研究产线

| 能力 | 脚本 | 输入 | 输出 | 关键依赖 | MCP 工具 |
|---|---|---|---|---|---|
| 列出 MCP 工具 | `scripts/list_mcp_tools_ws.py` | `ws(s)://...`、`X-API-Key` | 工具列表（stdout） | `websockets`（可选依赖） | `tools/list` |
| 调任意 MCP 工具 | `scripts/call_mcp_tool_ws.py` | `ws(s)://...`、tool name、JSON args | 工具返回（stdout） | `websockets` | `tools/call` |
| 单笔策略分析 | `scripts/mev_analysis_ws.py` | `ws(s)://...`、`tx_hash`、`max_steps` | 分析文本（stdout） | `websockets` | `get_eigenphi_tx_mev_analysis` |
| 批量拉摘要+分析并出报告 | `scripts/analyze_mev_txs_batch_ws.py` | `tx_hashes` / `--tx-file` | Markdown 报告 | `websockets` | `get_eigenphi_tx_mev`、`get_eigenphi_tx_mev_analysis` |
| 拉最新 MEV 并筛 ROI + 分析 | `scripts/latest_mev_roi_analysis_ws.py` | `tx_count`、`min_roi` | stdout + 可选 JSON | `websockets` | `get_eigenphi_latest_mev`、`get_eigenphi_tx_mev_analysis` |
| 订阅/读取 MEV 实时流 | `scripts/mev_stream_ws.py` | `--stream seconds` | 实时推送（stdout） | `websockets` | `get_eigenphi_mev_stream` |
| EigenPhi analyseTransaction -> 图 | `scripts/eigenphi_token_flow_graph.py` | `tx_hash` 或 `--json` | `.svg` 或 `.mmd` 或 `.html` 或 DOT | `requests`；系统 `dot`（可选）；Python `graphviz`（可选） | 无（直接 EigenPhi HTTP API） |
| CMC 时点价查询（校验） | `scripts/query_cmc_wsteth_at_time.py` | `COINMARKETCAP_API_KEY`、timestamp | 原始 JSON（stdout） | `requests` | 无 |

研究输入的“样本集合”：
- `config/mev_roi_tx_hashes.txt`：一组 ROI>1 的 MEV tx_hash 输入集合（给批处理脚本复用）。

研究结论沉淀：
- `docs/development/ANALYSIS_MEV_ROI_11_TXS.md`：ROI 样本分析报告（结论型）。
- `docs/development/PNL_ANOMALY_0x082872cd.md`：PnL 异常溯源与复现命令（可复现型）。
- `docs/setup/MCP_COINGECKO_CMC.md`：CoinGecko/CMC MCP 配置指南（环境型）。

---

## 3. 仓库边界与提交策略（哪些进主干，哪些忽略）

下面给出“默认推荐”，并分别说明对两种产品形态的取舍。

### 3.1 必须进主干（两种形态都建议保留）

- 线上服务代码与文档：
  - `src/`、`templates/`、`static/`、`run.py`、`Dockerfile`、`render.yaml`
  - `docs/deployment/MEV_BLOCK_VIEWER.md` 等部署/路由文档
- 可复现的研究工具脚本（**前提：不引入重依赖进生产 requirements**）：
  - `scripts/*_ws.py`（MCP WebSocket 客户端族）
  - `scripts/eigenphi_token_flow_graph.py`（图生成器）
  - `scripts/query_cmc_wsteth_at_time.py`（价格校验脚本）
- 验证证据：
  - `TEST_VERIFICATION.md`

### 3.2 建议进主干（研究工具优先；线上服务视团队偏好）

- 研究报告/分析笔记（建议做“索引化管理”，否则长期会噪）：
  - 推荐目录：`docs/research/` 或 `docs/analysis/`
  - 当前文件：`docs/development/ANALYSIS_*.md`、`docs/development/PNL_ANOMALY_*.md`

### 3.3 默认应忽略（典型生成物/临时产物）

1) **图生成产物（单笔/临时）**  
这类通常每次运行脚本都会变化，不适合进主干：
- `token_flow_graphs/eigenphi_*.html`
- `token_flow_graphs/eigenphi_*.mmd`
- `token_flow_graphs/**/test_*.svg`

2) **大规模区块产物（批量生成）**  
对在线服务来说，“MEV Viewer”可以只保留少量样例块；其余块建议外置或忽略：
- `token_flow_graphs/block_*/`（除了明确要保留的样例块）

实现方式建议（更稳）：
- 把批量生成输出默认写到 `outputs/token_flow_graphs/`（仓库已忽略 `outputs/`）
- 在线服务通过环境变量指向产物目录（例如 `TOKEN_FLOW_GRAPHS_DIR`），缺省仍用 `token_flow_graphs/`

### 3.4 两种形态的“清晰边界建议”

**如果主干定位为 Online Service：**
- 强制：`requirements.txt` 只放线上必需依赖
- 推荐：研究侧依赖单独放 `requirements.research.txt`（如 `websockets`、`graphviz`）
- `scripts/` 允许入库，但默认当作“开发/运维工具”，不要求容器内可运行所有脚本
- `token_flow_graphs/`：只保留 1-2 个样例块目录，其余通过生成或外置提供

**如果主干定位为 Research Toolkit：**
- `scripts/` 与 `docs/` 是主资产：把研究产线做成“可复现闭环”
- `requirements.txt` 可拆分：
  - `requirements.txt`（线上/核心）
  - `requirements.dev.txt` 或 `requirements.research.txt`（websockets、graphviz 等可选）

---

## 4. 风险清单（Taleb 视角：尾部风险/不可控点）

- 外部数据源不稳定：EigenPhi / BlockSec 的接口字段与鉴权策略可能变化（需要快速降级与错误可观测性）。
- “生成物入库”导致 repo 膨胀：长期会拖慢 diff/merge/CI（必须有边界与忽略规则）。
- 依赖漂移：Graphviz 这类“Python 包 + 系统二进制”组合在容器里最容易踩坑（建议明确可选/必选）。

---

## 5. 验收标准（用于判断边界是否落地）

- `git status` 下不再出现明显“脚本运行产物”（如 `token_flow_graphs/eigenphi_*.html/.mmd`）
- `./run_tests.sh` 通过
- 新人只看本文件即可回答：
  - “线上服务入口有哪些？需要什么依赖？”
  - “研究工具怎么跑？用到哪些 MCP 工具？产物写到哪里？”
