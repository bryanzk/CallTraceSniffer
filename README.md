# CallTraceSniffer

`CallTraceSniffer` 是一个面向以太坊交易分析的 Flask Web/API 工具。当前版本的核心职责是把 BlockSec / EigenPhi / Dune / RPC 等外部数据源串起来，生成可复用的交易分析产物，包括 IR V1 JSON、Mermaid DAG、批量统计结果，以及按区块生成的 MEV 可视化页面。

项目已经不再是“只抓一个 BlockSec 页面”的早期原型。当前仓库同时承载：

- 单笔交易分析与 IR V1 生成
- BlockSec simulation URL 解析与“模拟即分析”
- 批量交易 / 批量 simulation URL 处理
- Uniswap pool 命中检查
- `tx metrics` 聚合查询（EigenPhi + Dune + RPC）
- MEV block HTML viewer 生成与静态资源分发
- 交易语义树、分阶段资金树、分析师报告等后续分析模块

## 主要能力

### 1. 交易分析主链路

- `POST /api/analyze`
  输入 `tx_hash`，输出：
  - `ir_v1`
  - `ir_v1_json`
  - `mermaid_dag`
  - `stats`

- `POST /api/trace`
  获取原始 BlockSec trace 数据，可作为调试或二次处理输入。

- `POST /api/ir_parse`
  直接返回 IR V1 JSON，便于脚本或下游系统消费。

- `POST /api/ir-to-mermaid`
  把已有 IR V1 JSON 转成 Mermaid DAG。

### 2. 模拟交易分析

- `POST /api/analyze-simulation`
  输入 BlockSec simulation URL，提取并分析模拟 trace。

- `POST /api/simulate-and-analyze`
  直接提交模拟参数到 BlockSec Simulation API，返回 simulation URL 与分析结果。
  这个接口依赖本地 BlockSec cookies。

- `POST /api/blocksec-cookies`
  上传 cookies JSON。

- `POST /api/blocksec-cookies/load`
  加载本地 cookies 文件并检查可用性。

- `POST /api/analyze-simulation-batch`
  批量处理 simulation URL。

### 3. 批量与辅助分析

- `POST /api/analyze-batch`
  上传 CSV，批量分析交易哈希。

- `POST /api/unipool/check`
  批量判断交易是否命中 Uniswap pool。

- `GET /api/unipool/status`
  查看 pool filter 缓存状态。

- `POST /api/tx-metrics-batch`
  聚合 EigenPhi、Dune、RPC 数据，返回 builder tip、coinbase transfer、revenue、block tx count 等指标。

### 4. MEV 区块查看器

- `POST /api/mev/block`
  按区块号生成或读取本地区块 MEV HTML 片段。

- `GET /mev/block/<block_number>`
  提供生成后的区块查看页面。

- `GET /mev/block/<block_number>/<filename>.svg`
  提供该页面引用的 SVG 资源。

## 架构概览

### Web 入口

- `run.py`
  根目录启动入口，负责把 `src/` 加入 Python 路径，并导出 `run:app` 供 `gunicorn` 使用。

- `src/calltrace/app.py`
  Flask 应用初始化、CORS、模板/静态目录配置、主页路由注册。

### API 层

- `src/calltrace/api/routes.py`
  主路由文件，涵盖交易分析、simulation、batch、MEV block、文件下载等接口。

- `src/calltrace/api/validators.py`
  请求体验证与基础参数清洗。

### 服务层

- `src/calltrace/services/analysis_service.py`
  单笔交易 / simulation 分析主服务。

- `src/calltrace/services/blocksec_adapter.py`
  调用外部 `blocksec-parser` HTTP 服务；默认地址是 `http://127.0.0.1:4444`。

- `src/calltrace/services/blocksec_simulation.py`
  BlockSec Simulation API 请求构造、cookies 解析、trace 查找。

- `src/calltrace/services/pool_filter_service.py`
  Uniswap pool 过滤。

- `src/calltrace/services/tx_metrics_service.py`
  Dune + EigenPhi + RPC 的指标聚合逻辑。

- `src/calltrace/services/mev_block_service.py`
  生成区块级 MEV viewer HTML / SVG 资源。

- `src/calltrace/services/staged_fundflow_tree.py`
  从交易 payload 构建分阶段资金树。

- `src/calltrace/services/semantic_report.py`
  渲染分析师报告 Markdown。

### 工具与资源

- `templates/index.html`
  当前 Web UI。

- `scripts/`
  命令行辅助脚本，包括 MEV block、tx metrics、EigenPhi token flow graph 等。

- `token_flow_graphs/`
  MEV block viewer 的静态输出目录。

- `outputs/`
  本地分析产物样例目录。

## 环境要求

### 必需

- Python `3.11+`
- `pip install -r requirements.txt`
- `playwright install chromium`

### 运行主分析链路时的外部依赖

- `blocksec-parser` HTTP 服务
  - 环境变量：`BLOCKSEC_PARSER_API_BASE_URL`
  - 默认值：`http://127.0.0.1:4444`

### 可选但常用

- `DUNE_API_KEY`
  启用 `unipool` 查询和 `tx metrics`。

- `DUNE_TX_QUERY_ID`
  `tx metrics` 使用的 Dune query id，默认 `6569281`。

- `ETH_RPC_URL`
  让 `tx metrics` 能读取区块交易总数等链上数据。

- `EIGENPHI_BASE_URL`
  EigenPhi 交易 JSON 地址模板，默认：
  `https://storage.googleapis.com/eigenphi-ethereum-tx/{tx_hash}`

- `BLOCKSEC_COOKIE` / `BLOCKSEC_COOKIE_FILE`
  支持 `simulate-and-analyze`、simulation 页面抓取等路径。
  默认 cookies 文件为根目录下的 `blocksec_cookies.json`。

- `MCP_EIGENPHI_SERVER`
  生成区块级 MEV 页面时使用的 MCP server 路径。

## 快速开始

### 本地开发

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
python run.py
```

默认监听：`http://127.0.0.1:5001`

如果需要补充环境变量，可以在仓库根目录放置 `.env`。`src/calltrace/config.py` 会自动加载该文件。

### 推荐 `.env` 示例

```dotenv
PORT=5001
HOST=0.0.0.0
DEBUG=True
BLOCKSEC_PARSER_API_BASE_URL=http://127.0.0.1:4444
DUNE_API_KEY=your_dune_api_key
DUNE_TX_QUERY_ID=6569281
ETH_RPC_URL=https://eth-mainnet.example/v2/your_key
BLOCKSEC_COOKIE_FILE=./blocksec_cookies.json
```

### Docker

```bash
docker compose up --build
```

或：

```bash
docker build -t calltrace-sniffer:latest .
docker run --rm -p 5001:5001 calltrace-sniffer:latest
```

`Dockerfile` 会安装 Python 依赖和 Playwright Chromium；容器启动时优先走 `gunicorn`，否则回退到 `python3 run.py`。

## 常用 API 示例

### 分析单笔交易

```bash
curl -X POST http://127.0.0.1:5001/api/analyze \
  -H 'Content-Type: application/json' \
  -d '{"tx_hash":"0x..."}'
```

### 批量查询 tx metrics

```bash
curl -X POST http://127.0.0.1:5001/api/tx-metrics-batch \
  -H 'Content-Type: application/json' \
  -d '{"tx_hashes":["0x...", "0x..."]}'
```

### 生成区块级 MEV viewer

```bash
curl -X POST http://127.0.0.1:5001/api/mev/block \
  -H 'Content-Type: application/json' \
  -d '{"block_number":24279007,"refresh":false}'
```

## 测试与验证

仓库约定的优先验证入口是：

```bash
python3 test_runner.py
```

它会直接转发到 `pytest`。

如果只想跑局部测试，也可以使用：

```bash
pytest tests/unit -q
pytest tests/integration -q
pytest -m smoke -q
```

当前仓库中可见的测试文件规模为：

- `42` 个 unit test 文件
- `5` 个 integration test 文件

## 仓库结构

```text
.
├── run.py
├── src/calltrace/
│   ├── app.py
│   ├── config.py
│   ├── api/
│   ├── services/
│   ├── utils/
│   └── models/
├── templates/
├── static/
├── scripts/
├── tests/
├── docs/
├── token_flow_graphs/
├── outputs/
├── Dockerfile
├── docker-compose.yml
└── test_runner.py
```

## 相关文档

- [docs/README.md](docs/README.md)
- [docs/development/API_ROUTES.md](docs/development/API_ROUTES.md)
- [docs/development/README.md](docs/development/README.md)
- [docs/development/README_WEB.md](docs/development/README_WEB.md)
- [docs/development/DATA_FLOW.md](docs/development/DATA_FLOW.md)
- [docs/development/IR_SPEC.md](docs/development/IR_SPEC.md)
- [docs/deployment/README_DOCKER.md](docs/deployment/README_DOCKER.md)
- [docs/deployment/QUICKSTART_DOCKER.md](docs/deployment/QUICKSTART_DOCKER.md)
- [tests/README.md](tests/README.md)

## 已知边界

- 主分析链路依赖外部 `blocksec-parser` 服务；如果该服务不可达，`/api/analyze`、`/api/trace`、`/api/ir_parse` 等接口会失败。
- `simulate-and-analyze` 依赖有效的 BlockSec cookies；没有 cookies 时会返回权限或抓取失败错误。
- `tx metrics` 的完整结果依赖 Dune、EigenPhi 和 RPC；缺少任一数据源时，返回字段可能退化或整体失败。
- MEV block viewer 需要本地可写的 `token_flow_graphs/` 目录，并依赖对应的 MCP/EigenPhi 侧能力。

## 开发建议

- 修改路由或能力说明时，同步更新 `README.md`、`docs/development/API_ROUTES.md` 和相关测试。
- 新增外部依赖时，优先在 `src/calltrace/config.py` 收口环境变量，并在 README 中补充运行前提。
- 若只调试文档，不要顺手改动 `local/`、`outputs/`、`data/` 等本地产物目录。
