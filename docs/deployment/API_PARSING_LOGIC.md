# API 解析逻辑调用链

本文档详细说明三个主要 API 端点背后的解析逻辑和调用链。

## 📋 API 端点概览

- `POST /api/analyze` - 分析单个交易
- `POST /api/analyze-batch` - 批量分析交易（最多10个）
- `POST /api/ir_parse` - 获取 IR V1 JSON

---

## 🔄 完整调用链

```
API 请求
  ↓
路由处理 (routes.py)
  ↓
数据提取 (BlockSecExtractor)
  ↓
Playwright 浏览器自动化
  ↓
BlockSec 页面数据抓取
  ↓
Trace 数据解析
  ↓
IR V1 构建 (build_blocksec_ir)
  ↓
统计分析 (process_tx_data)
  ↓
返回结果
```

---

## 1️⃣ POST /api/analyze - 分析单个交易

### 调用流程

```python
# 位置: src/calltrace/api/routes.py (198-244行)

@app.route('/api/analyze', methods=['POST'])
def analyze_tx():
    # 1. 参数验证
    tx_hash = request.json.get('tx_hash')
    
    # 2. 数据提取 - 调用 BlockSecExtractor
    extractor = BlockSecExtractor()
    result = asyncio.run(extractor.extract_blocksec_data(tx_hash))
    #    ↓
    #    BlockSecExtractor.extract_blocksec_data()
    #    ↓
    #    BlockSecExtractor._extract_trace_from_page()
    #    ↓
    #    Playwright 浏览器自动化
    #    - 打开 BlockSec 页面
    #    - 监听网络响应
    #    - 提取 trace 数据
    
    # 3. 数据处理 - 调用 process_tx_data
    analysis = process_tx_data(trace_data, tx_hash)
    #    ↓
    #    build_blocksec_ir(trace_data, tx_hash)  # IR V1 构建
    #    ↓
    #    _count_ir_nodes()  # 统计 swap/transfer 数量
    #    ↓
    #    _compute_flow_counts()  # 计算流量统计
    #    ↓
    #    _extract_total_gas()  # 提取 Gas 使用量
    
    # 4. 返回结果
    return jsonify({...})
```

### 核心服务调用

#### 1. BlockSecExtractor (数据提取)

**文件**: `src/calltrace/services/extractor.py`

**主要方法**:
- `extract_blocksec_data(tx_hash)` - 提取交易数据
  - 构建 BlockSec URL: `https://app.blocksec.com/explorer/tx/eth/{tx_hash}/`
  - 调用 `_extract_trace_from_page(url)`

- `_extract_trace_from_page(url)` - 从页面提取 trace 数据
  - 使用 **Playwright** 启动 Chromium 浏览器
  - 访问 BlockSec 页面
  - 监听网络响应，拦截包含 `/api/` 的请求
  - 从响应中提取包含 `dataMap` 和 `mainTrace` 的数据
  - 等待 15 秒确保数据加载完成

**关键技术**:
- **Playwright**: 浏览器自动化框架
- **异步编程**: 使用 `async/await`
- **网络拦截**: 监听页面网络响应

#### 2. build_blocksec_ir (IR V1 构建)

**文件**: `src/calltrace/services/ir_v1_blocksec.py`

**功能**: 将 BlockSec 的 trace 数据转换为 IR V1 格式

**主要步骤**:
1. **收集日志** (`_collect_logs`): 从 `dataMap` 中提取所有事件日志
2. **识别 Swap 事件**: 
   - V3 Swap: `TOPIC_V3 = 0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67`
   - V4 Swap: `TOPIC_V4 = 0x40e9cecb9f5f1f1c5b9c97dec2917b7ee92e57ba5563708daca94dd84ad7112f`
   - V2 Swap: `TOPIC_V2 = 0xd78ad95fa46c994b6551d0da85fc275fe613ce37657fb8d5e3d130840159d822`
3. **识别 Transfer 事件**: `TOPIC_TRANSFER = 0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef`
4. **构建调用树**: 从 `mainTrace` 构建嵌套的调用结构
5. **关联事件**: 将 Swap/Transfer 事件关联到对应的调用节点
6. **规范化地址**: 使用 `POOL_ID_CANONICAL` 映射规范化池地址

#### 3. process_tx_data (数据处理和统计)

**文件**: `src/calltrace/api/routes.py` (170-192行)

**功能**: 处理 trace 数据并生成统计信息

**调用的辅助函数**:

- `_count_ir_nodes(node)` - 递归统计 IR 树中的 swap 和 transfer 节点数量
- `_compute_flow_counts(trace_data)` - 计算流量统计
  - `_extract_transfer_edges()` - 提取所有 transfer 边
  - 识别 Router 地址（来自 `config.ROUTER_ADDRESSES`）
  - 分类流量类型：Virtual、Transfer、Direct
  - 合并匹配的流入/流出边
- `_extract_total_gas(trace_data)` - 从 `gasFlame` 中提取总 Gas 使用量

---

## 2️⃣ POST /api/analyze-batch - 批量分析

### 调用流程

```python
# 位置: src/calltrace/api/routes.py (291-364行)

@app.route('/api/analyze-batch', methods=['POST'])
def analyze_batch_tx():
    # 1. 读取 CSV 文件
    tx_hashes = [从 CSV 读取]
    
    # 2. 循环处理每个交易
    for tx_hash in tx_hashes:
        # 对每个交易调用相同的逻辑
        extractor = BlockSecExtractor()
        result = asyncio.run(extractor.extract_blocksec_data(tx_hash))
        analysis = process_tx_data(trace_data, tx_hash)
        # ... 与 /api/analyze 相同的处理流程
    
    # 3. 返回所有结果
    return jsonify({'results': [...], 'total': len(results)})
```

**注意**: 批量分析是串行处理的，每个交易都会：
1. 启动 Playwright 浏览器
2. 访问 BlockSec 页面
3. 提取数据
4. 构建 IR V1
5. 生成统计信息

---

## 3️⃣ POST /api/ir_parse - 获取 IR V1 JSON

### 调用流程

```python
# 位置: src/calltrace/api/routes.py (405-447行)

@app.route('/api/ir_parse', methods=['POST'])
def get_ir_v1():
    # 1. 检查缓存
    if tx_hash in extracted_data_cache:
        return cached_ir_json
    
    # 2. 如果没有缓存，执行完整流程
    extractor = BlockSecExtractor()
    result = asyncio.run(extractor.extract_blocksec_data(tx_hash))
    analysis = process_tx_data(trace_data, tx_hash)
    # ... 与 /api/analyze 相同的处理流程
    
    # 3. 只返回 IR V1 JSON（不包含 stats）
    return app.response_class(analysis['ir_v1_json'], mimetype='application/json')
```

**区别**: 这个端点只返回 IR V1 JSON，不包含统计信息。

---

## 📦 核心服务模块

### 1. BlockSecExtractor (`src/calltrace/services/extractor.py`)

**职责**: 从 BlockSec 网站提取交易 trace 数据

**主要方法**:
- `extract_blocksec_data(tx_hash)` - 提取普通交易数据
- `extract_blocksec_simulation_data(sim_url)` - 提取模拟交易数据
- `_extract_trace_from_page(url)` - 使用 Playwright 从页面提取数据
- `_find_trace_payload(payload)` - 在响应中查找 trace 数据
- `parse_simulation_url(sim_url)` - 解析模拟交易 URL

**依赖**:
- `playwright` - 浏览器自动化
- `asyncio` - 异步处理

### 2. ir_v1_blocksec (`src/calltrace/services/ir_v1_blocksec.py`)

**职责**: 将 BlockSec trace 数据转换为 IR V1 格式

**主要函数**:
- `build_blocksec_ir(trace_data, tx_hash)` - 主函数，构建 IR V1
- `_collect_logs(trace_data)` - 收集所有事件日志
- `_canonical_pool_id(pool_id)` - 规范化池地址
- `_parse_int(value)` - 解析整数值

**关键常量**:
- `TOPIC_V3`, `TOPIC_V4`, `TOPIC_V2` - Swap 事件主题
- `TOPIC_TRANSFER` - Transfer 事件主题
- `POOL_ID_CANONICAL` - 池地址映射
- `TOKEN_DECIMALS` - Token 精度映射

### 3. routes.py 辅助函数

**数据处理函数**:
- `process_tx_data(trace_data, tx_hash)` - 主处理函数
- `_count_ir_nodes(node)` - 统计节点数量
- `_compute_flow_counts(trace_data)` - 计算流量统计
- `_extract_transfer_edges(trace_data)` - 提取 transfer 边
- `_extract_total_gas(trace_data)` - 提取 Gas
- `_order_ir_payload(payload, tx_hash)` - 排序 IR 数据
- `_serialize_ir_payload(payload, tx_hash)` - 序列化为 JSON

---

## 🔍 数据流转详解

### 步骤 1: 数据提取

```
用户输入 tx_hash
  ↓
BlockSecExtractor.extract_blocksec_data()
  ↓
构建 URL: https://app.blocksec.com/explorer/tx/eth/{tx_hash}/
  ↓
Playwright 启动浏览器
  ↓
访问 BlockSec 页面
  ↓
监听网络响应 (page.on('response'))
  ↓
拦截包含 "/api/" 的响应
  ↓
解析 JSON 响应
  ↓
查找包含 dataMap 和 mainTrace 的数据
  ↓
返回 trace_data
```

### 步骤 2: IR V1 构建

```
trace_data (BlockSec 格式)
  ↓
build_blocksec_ir(trace_data, tx_hash)
  ↓
收集所有日志 (_collect_logs)
  ↓
识别 Swap 事件 (通过 topics 匹配)
  ↓
识别 Transfer 事件 (通过 topics 匹配)
  ↓
构建调用树 (从 mainTrace)
  ↓
关联事件到调用节点
  ↓
规范化地址和金额
  ↓
返回 ir_v1 (Python dict)
```

### 步骤 3: 统计分析

```
ir_v1 + trace_data
  ↓
process_tx_data()
  ↓
_count_ir_nodes() → swaps_count, transfers_count
  ↓
_compute_flow_counts() → router_count, direct_count, virtual_count
  ↓
_extract_total_gas() → total_gas
  ↓
返回 stats 字典
```

### 步骤 4: 序列化

```
ir_v1 (Python dict)
  ↓
_order_ir_payload() → 确保 tx_hash 在第一位
  ↓
json.dumps() → JSON 字符串
  ↓
ir_v1_json
```

---

## ⚙️ 配置依赖

### config.py

**关键配置**:
- `ROUTER_ADDRESSES` - Router 地址列表，用于流量分类
- `WETH`, `USDC` - 常见 Token 地址
- `TRANSFER_SELECTOR` - Transfer 函数选择器

### 环境要求

- **Playwright**: 需要安装 Chromium 浏览器
- **系统依赖**: 见 `Dockerfile`，包括 libasound2, libatk 等

---

## 🎯 关键数据格式

### 输入: trace_data (BlockSec 格式)

```json
{
  "dataMap": {
    "node_id": {
      "invocation": {...},
      "event": {...},
      "nodeType": 1
    }
  },
  "mainTrace": {
    "name": "...",
    "children": [...]
  },
  "gasFlame": [...]
}
```

### 输出: ir_v1 (IR V1 格式)

```json
{
  "tx_hash": "0x...",
  "rootTrace": {
    "type": "swap",
    "address": "0x...",
    "amountIn": "...",
    "amountOut": "...",
    "callback": [...]
  }
}
```

---

## 🔧 性能考虑

### 时间消耗

1. **Playwright 启动**: ~2-5 秒
2. **页面加载**: ~5-10 秒
3. **等待数据**: 15 秒（固定等待）
4. **IR 构建**: ~1-2 秒
5. **总计**: 通常 30-60 秒，最长可能 120 秒

### 优化建议

1. **缓存机制**: 已实现 `extracted_data_cache`
2. **批量处理**: 串行处理，避免并发过多
3. **超时设置**: API 客户端应设置 300 秒超时

---

## 📚 相关文件

- `src/calltrace/api/routes.py` - API 路由定义
- `src/calltrace/services/extractor.py` - 数据提取服务
- `src/calltrace/services/ir_v1_blocksec.py` - IR V1 构建服务
- `src/calltrace/config.py` - 配置管理

---

## 🔗 相关文档

- [IR 规范文档](../development/IR_SPEC.md) - IR V1 格式规范
- [数据流转文档](../development/DATA_FLOW.md) - 数据流转过程
- [API 使用指南](./API_USAGE.md) - API 使用说明
