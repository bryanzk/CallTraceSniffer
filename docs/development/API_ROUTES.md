# API 路由文档

## 📋 概述

本文档描述 CallTraceSniffer 的所有 API 端点、请求/响应格式，以及端到端的请求处理流程。

## 🌐 API 端点列表

| 端点 | 方法 | 描述 | 认证 |
|------|------|------|------|
| `/api/analyze` | POST | 分析单个交易 | 无 |
| `/api/analyze-simulation` | POST | 分析模拟交易 | 无 |
| `/api/simulate-and-analyze` | POST | 模拟并分析交易 | 需Cookie |
| `/api/analyze-batch` | POST | 批量分析交易 | 无 |
| `/api/analyze-simulation-batch` | POST | 批量分析模拟交易 | 无 |
| `/api/ir_parse` | POST | 获取 IR V1 JSON | 无 |
| `/api/ir-to-mermaid` | POST | IR 转 Mermaid | 无 |
| `/api/download-result` | POST | 下载分析结果 | 无 |
| `/api/blocksec-cookies` | POST | 上传 Cookie | 无 |
| `/api/blocksec-cookies/load` | POST | 加载本地 Cookie | 无 |

## 📊 端点详情

### 1. 分析单个交易

**端点**: `POST /api/analyze`

**请求**:
```json
{
  "tx_hash": "0x1234567890abcdef..."
}
```

**响应（成功）**:
```json
{
  "success": true,
  "tx_hash": "0x1234...",
  "ir_v1": {
    "tx_hash": "0x1234...",
    "pattern": "swap",
    "rootTrace": {...}
  },
  "ir_v1_json": "{ ... }",
  "mermaid_dag": "graph TD\n  N1[...]",
  "stats": {
    "swaps_count": 2,
    "transfers_count": 3,
    "router_count": 1,
    "direct_count": 2,
    "virtual_count": 0,
    "total_gas": 150000
  }
}
```

**响应（失败）**:
```json
{
  "success": false,
  "error": "错误信息"
}
```

**端到端流程**:
```
┌────────────────────────────────────────────────────────────────┐
│                    POST /api/analyze                            │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────┐
│  1. 请求验证                                                    │
│     └─ parse_json_object(request)                              │
│     └─ validate_tx_hash(data)                                  │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────┐
│  2. 调用分析服务                                                │
│     └─ analysis_service.analyze_tx(tx_hash)                    │
│        ├─ extractor.extract_blocksec_data(tx_hash)             │
│        ├─ process_tx_data(trace_data)                          │
│        └─ build_mermaid_dag(ir_v1)                             │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────┐
│  3. 构建响应                                                    │
│     └─ _response_from_service_result(result)                   │
└────────────────────────────────────────────────────────────────┘
```

---

### 2. 分析模拟交易

**端点**: `POST /api/analyze-simulation`

**请求**:
```json
{
  "simulation_url": "https://app.blocksec.com/explorer/tx/eth/0x...?event=simulation"
}
```

**响应**: 与 `/api/analyze` 相同

**端到端流程**:
```
POST /api/analyze-simulation
         │
         ▼
┌─────────────────────────────────────┐
│  1. 验证 simulation_url             │
│     └─ validate_simulation_url()    │
└─────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│  2. 解析 URL 获取 tx_hash           │
│     └─ parse_simulation_url()       │
└─────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│  3. 提取模拟数据                     │
│     └─ extract_blocksec_simulation_data() │
└─────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│  4. 转换为 IR                        │
│     └─ process_tx_data()            │
└─────────────────────────────────────┘
```

---

### 3. 模拟并分析交易

**端点**: `POST /api/simulate-and-analyze`

**请求**:
```json
{
  "params": {
    "sender": "0x...",
    "receiver": "0x...",
    "inputData": "0x...",
    "value": "1.5",
    "chainID": 1
  }
}
```

或使用完整参数：
```json
{
  "simulation_params": {
    "chainID": 1,
    "simulationType": 0,
    "from": "0x...",
    "to": "0x...",
    "data": "0x...",
    "value": "1500000000000000000"
  }
}
```

**响应（成功）**:
```json
{
  "success": true,
  "tx_hash": "0x...",
  "simulation_id": "sim_123...",
  "simulation_url": "https://app.blocksec.com/...",
  "ir_v1": {...},
  "ir_v1_json": "...",
  "stats": {...}
}
```

**端到端流程**:
```
POST /api/simulate-and-analyze
         │
         ▼
┌─────────────────────────────────────┐
│  1. 构建模拟请求                     │
│     └─ build_simulation_request_payload() │
│        ├─ 标准化参数                │
│        └─ ETH → Wei 转换            │
└─────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│  2. 发送模拟请求                     │
│     └─ run_simulation_with_payload() │
│        ├─ 加载 BlockSec cookies     │
│        └─ POST BlockSec API         │
└─────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│  3. 获取追踪数据                     │
│     ├─ 方式A: 从响应获取             │
│     └─ 方式B: Playwright 抓取       │
└─────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│  4. 转换为 IR                        │
│     └─ process_tx_data()            │
└─────────────────────────────────────┘
```

---

### 4. 批量分析交易

**端点**: `POST /api/analyze-batch`

**请求**: multipart/form-data
```
file: CSV文件（每行一个tx_hash）
```

**响应**:
```json
{
  "success": true,
  "total": 3,
  "results": [
    {
      "tx_hash": "0x...",
      "success": true,
      "ir_v1": {...},
      "stats": {...}
    },
    {
      "tx_hash": "0x...",
      "success": false,
      "error": "无法提取数据"
    }
  ]
}
```

**限制**: 最多 10 个交易

---

### 5. 批量分析模拟交易

**端点**: `POST /api/analyze-simulation-batch`

**请求**:
```json
{
  "simulation_urls": [
    "https://app.blocksec.com/...",
    "https://app.blocksec.com/..."
  ]
}
```

**响应**: 与批量分析类似

**限制**: 最多 10 个交易

---

### 6. 获取 IR V1 JSON

**端点**: `POST /api/ir_parse`

**请求**:
```json
{
  "tx_hash": "0x..."
}
```

**响应**: 直接返回 IR V1 JSON（Content-Type: application/json）

**流程**:
1. 先检查缓存
2. 缓存未命中则提取数据
3. 返回序列化的 IR JSON

---

### 7. IR 转 Mermaid

**端点**: `POST /api/ir-to-mermaid`

**请求**:
```json
{
  "ir_v1": {
    "tx_hash": "0x...",
    "rootTrace": {...}
  }
}
```

**响应**:
```json
{
  "success": true,
  "mermaid_dag": "graph TD\n  N1[...]..."
}
```

---

### 8. 下载分析结果

**端点**: `POST /api/download-result`

**请求**:
```json
{
  "tx_hash": "0x...",
  "output_type": "ir_v1"
}
```

**响应**: 文件下载（application/json）

---

### 9. Cookie 管理

#### 上传 Cookie

**端点**: `POST /api/blocksec-cookies`

**请求**: multipart/form-data
```
cookie_file: JSON文件
```

**响应**:
```json
{
  "success": true,
  "path": "/path/to/blocksec_cookies.json"
}
```

#### 加载本地 Cookie

**端点**: `POST /api/blocksec-cookies/load`

**响应**:
```json
{
  "success": true,
  "path": "/path/to/blocksec_cookies.json"
}
```

## 🔄 请求处理架构

### 分层架构

```
┌─────────────────────────────────────────────────────────────────┐
│                       API 层 (routes.py)                         │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  • 请求验证 (validators.py)                              │    │
│  │  • 参数解析                                              │    │
│  │  • 响应格式化                                            │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    服务层 (services/)                            │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  AnalysisService    - 分析协调器                         │    │
│  │  BlockSecExtractor  - 数据提取                           │    │
│  │  blocksec_simulation - 模拟服务                          │    │
│  │  ir_v1_blocksec     - IR 构建                           │    │
│  │  mermaid_dag        - Mermaid 生成                       │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    工具层 (utils/)                               │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  analysis_utils  - 分析工具函数                          │    │
│  │  address         - 地址处理                              │    │
│  │  ir_format       - IR 格式化                             │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

### 依赖注入

```python
def register_routes(app, extracted_data_cache):
    # 1. 创建配置对象
    router_config = RouterConfig.from_global_config()
    
    # 2. 创建服务实例（注入依赖）
    analysis_service = AnalysisService(
        cache=extracted_data_cache,
        router_config=router_config
    )
    
    # 3. 注册路由
    @app.route('/api/analyze', methods=['POST'])
    def analyze_tx():
        result = analysis_service.analyze_tx(tx_hash)
        return _response_from_service_result(result)
```

## 📝 验证规则

### 交易哈希验证

```python
def validate_tx_hash(data: dict) -> Tuple[str, Optional[str]]:
    tx_hash = data.get('tx_hash', '').strip()
    
    if not tx_hash:
        return '', '交易哈希不能为空'
    
    if not tx_hash.startswith('0x') or len(tx_hash) != 66:
        return '', '无效的交易哈希格式'
    
    return tx_hash, None
```

### 模拟 URL 验证

```python
def validate_simulation_url(data: dict) -> Tuple[str, Optional[str]]:
    sim_url = data.get('simulation_url', '').strip()
    
    if not sim_url:
        return '', '模拟URL不能为空'
    
    # 进一步验证由 BlockSecExtractor.parse_simulation_url 处理
    return sim_url, None
```

## 🚨 错误处理

### HTTP 状态码

| 状态码 | 场景 |
|--------|------|
| 200 | 请求成功 |
| 400 | 请求参数错误 |
| 403 | BlockSec Cookie 失效 |
| 404 | 资源未找到 |
| 500 | 服务器内部错误 |

### 错误响应格式

```json
{
  "success": false,
  "error": "错误描述信息"
}
```

### 常见错误

| 错误信息 | 原因 | 解决方案 |
|----------|------|----------|
| 交易哈希不能为空 | 未提供 tx_hash | 检查请求体 |
| 无效的交易哈希格式 | 格式不正确 | 使用完整的 0x 开头 66 位哈希 |
| 无法提取交易数据 | 网络/页面错误 | 重试或检查网络 |
| 未找到trace数据 | BlockSec 无数据 | 确认交易存在 |
| API 请求被拒绝 (403) | Cookie 失效 | 更新 BlockSec cookies |

## 📊 响应结构

### 成功响应

```python
def _response_from_service_result(result: ServiceResult):
    if result.ok:
        return jsonify({
            'success': True,
            'tx_hash': result.payload['tx_hash'],
            'ir_v1': result.payload['analysis']['ir_v1'],
            'ir_v1_json': result.payload['analysis']['ir_v1_json'],
            'mermaid_dag': result.payload['mermaid_dag'],
            'stats': result.payload['analysis']['stats']
        })
```

### Stats 结构

```json
{
  "swaps_count": 2,       // swap 操作数量
  "transfers_count": 5,   // 总转账数量
  "router_count": 2,      // 通过 Router 的转账
  "direct_count": 2,      // 直接转账
  "virtual_count": 1,     // 虚拟转账（自转）
  "total_gas": 150000     // 总 Gas 消耗
}
```

## 🔧 使用示例

### cURL 示例

```bash
# 分析单个交易
curl -X POST http://localhost:5001/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"tx_hash": "0x1234..."}'

# 分析模拟交易
curl -X POST http://localhost:5001/api/analyze-simulation \
  -H "Content-Type: application/json" \
  -d '{"simulation_url": "https://app.blocksec.com/..."}'

# IR 转 Mermaid
curl -X POST http://localhost:5001/api/ir-to-mermaid \
  -H "Content-Type: application/json" \
  -d '{"ir_v1": {"tx_hash": "0x...", "rootTrace": {...}}}'
```

### Python 示例

```python
import requests

# 分析交易
response = requests.post(
    "http://localhost:5001/api/analyze",
    json={"tx_hash": "0x1234..."}
)
result = response.json()

if result["success"]:
    ir_v1 = result["ir_v1"]
    stats = result["stats"]
    mermaid = result["mermaid_dag"]
```

## 📈 性能考虑

### 响应时间

| 端点 | 典型响应时间 | 说明 |
|------|-------------|------|
| /api/analyze | 15-30秒 | 需要 Playwright 抓取 |
| /api/analyze-simulation | 15-30秒 | 需要 Playwright 抓取 |
| /api/simulate-and-analyze | 5-15秒 | API 调用 + 可能抓取 |
| /api/ir-to-mermaid | <100ms | 纯计算 |
| /api/ir_parse (缓存命中) | <100ms | 直接返回缓存 |

### 缓存策略

- 分析结果缓存在内存中
- 缓存键：tx_hash
- 生命周期：应用运行期间

### 并发限制

- 批量 API 限制：最多 10 个交易
- Playwright 实例：单例模式
