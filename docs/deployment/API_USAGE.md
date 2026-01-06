# API 使用指南

本文档介绍如何访问和使用 CallTraceSniffer 的 API 接口。

## 🌐 API 基础地址

**生产环境（Railway）:**
```
https://calltracesniffer-production.up.railway.app
```

## 📋 API 端点列表

### 1. 分析单个交易

**端点**: `POST /api/analyze`

**功能**: 根据交易哈希分析交易并返回 IR V1 JSON

**请求示例**:

```bash
curl -X POST https://calltracesniffer-production.up.railway.app/api/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "tx_hash": "0x5336739d401392b2d40043a9eac4396d45e1c2d9e606a62bd984b0a72f2931ff"
  }'
```

**请求体**:
```json
{
  "tx_hash": "0x5336739d401392b2d40043a9eac4396d45e1c2d9e606a62bd984b0a72f2931ff"
}
```

**响应示例**:
```json
{
  "success": true,
  "tx_hash": "0x5336739d401392b2d40043a9eac4396d45e1c2d9e606a62bd984b0a72f2931ff",
  "ir_v1": {
    "tx_hash": "0x5336739d401392b2d40043a9eac4396d45e1c2d9e606a62bd984b0a72f2931ff",
    "rootTrace": { ... }
  },
  "ir_v1_json": "{ ... }",
  "stats": {
    "swaps_count": 2,
    "transfers_count": 5,
    "router_count": 3,
    "direct_count": 2,
    "virtual_count": 0,
    "total_gas": 150000
  }
}
```

---

### 2. 分析模拟交易

**端点**: `POST /api/analyze-simulation`

**功能**: 根据 BlockSec 模拟交易 URL 分析交易

**请求示例**:

```bash
curl -X POST https://calltracesniffer-production.up.railway.app/api/analyze-simulation \
  -H "Content-Type: application/json" \
  -d '{
    "simulation_url": "https://app.blocksec.com/explorer/tx/eth/0x5336739d401392b2d40043a9eac4396d45e1c2d9e606a62bd984b0a72f2931ff?event=simulation"
  }'
```

**请求体**:
```json
{
  "simulation_url": "https://app.blocksec.com/explorer/tx/eth/0x...?event=simulation"
}
```

**响应格式**: 与 `/api/analyze` 相同

---

### 3. 批量分析交易

**端点**: `POST /api/analyze-batch`

**功能**: 批量分析多个交易（最多 10 个）

**请求示例**:

```bash
curl -X POST https://calltracesniffer-production.up.railway.app/api/analyze-batch \
  -F "file=@tx_hashes.csv"
```

**CSV 文件格式** (`tx_hashes.csv`):
```csv
0x5336739d401392b2d40043a9eac4396d45e1c2d9e606a62bd984b0a72f2931ff
0xe42c7f10664571e96b425333a7a06fae1de65dd30eb871d84ceb559cceed00a6
0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef
```

**响应示例**:
```json
{
  "success": true,
  "results": [
    {
      "tx_hash": "0x5336...",
      "success": true,
      "ir_v1": { ... },
      "ir_v1_json": "{ ... }",
      "stats": { ... }
    },
    {
      "tx_hash": "0xe42c...",
      "success": false,
      "error": "无法提取交易数据"
    }
  ],
  "total": 2
}
```

---

### 4. 获取 IR V1 JSON

**端点**: `POST /api/ir_parse`

**功能**: 直接返回 IR V1 JSON（Content-Type: application/json）

**请求示例**:

```bash
curl -X POST https://calltracesniffer-production.up.railway.app/api/ir_parse \
  -H "Content-Type: application/json" \
  -d '{
    "tx_hash": "0x5336739d401392b2d40043a9eac4396d45e1c2d9e606a62bd984b0a72f2931ff"
  }'
```

**响应**: 直接返回 IR V1 JSON 格式

---

### 5. 下载分析结果

**端点**: `POST /api/download-result`

**功能**: 下载分析结果为 JSON 文件

**请求示例**:

```bash
curl -X POST https://calltracesniffer-production.up.railway.app/api/download-result \
  -H "Content-Type: application/json" \
  -d '{
    "tx_hash": "0x5336739d401392b2d40043a9eac4396d45e1c2d9e606a62bd984b0a72f2931ff",
    "output_type": "ir_v1"
  }' \
  --output result.json
```

**请求体**:
```json
{
  "tx_hash": "0x5336739d401392b2d40043a9eac4396d45e1c2d9e606a62bd984b0a72f2931ff",
  "output_type": "ir_v1"
}
```

**响应**: 返回 JSON 文件下载

---

## 💻 客户端代码示例

### Python

```python
import requests

BASE_URL = "https://calltracesniffer-production.up.railway.app"

# 分析单个交易
def analyze_tx(tx_hash: str):
    response = requests.post(
        f"{BASE_URL}/api/analyze",
        json={"tx_hash": tx_hash},
        timeout=300  # Playwright 可能需要较长时间
    )
    return response.json()

# 使用示例
result = analyze_tx("0x5336739d401392b2d40043a9eac4396d45e1c2d9e606a62bd984b0a72f2931ff")
if result.get("success"):
    print(f"交易哈希: {result['tx_hash']}")
    print(f"Swap 数量: {result['stats']['swaps_count']}")
    print(f"Transfer 数量: {result['stats']['transfers_count']}")
    print(f"总 Gas: {result['stats']['total_gas']}")
else:
    print(f"错误: {result.get('error')}")

# 批量分析
def analyze_batch(tx_hashes: list):
    # 创建临时 CSV 文件
    import csv
    import io
    
    csv_data = io.StringIO()
    writer = csv.writer(csv_data)
    for tx_hash in tx_hashes:
        writer.writerow([tx_hash])
    
    files = {'file': ('tx_hashes.csv', csv_data.getvalue().encode())}
    response = requests.post(
        f"{BASE_URL}/api/analyze-batch",
        files=files,
        timeout=600
    )
    return response.json()

# 使用示例
tx_hashes = [
    "0x5336739d401392b2d40043a9eac4396d45e1c2d9e606a62bd984b0a72f2931ff",
    "0xe42c7f10664571e96b425333a7a06fae1de65dd30eb871d84ceb559cceed00a6"
]
results = analyze_batch(tx_hashes)
for item in results.get("results", []):
    if item.get("success"):
        print(f"✅ {item['tx_hash']}: {item['stats']['swaps_count']} swaps")
    else:
        print(f"❌ {item['tx_hash']}: {item.get('error')}")
```

### JavaScript/TypeScript

```javascript
const BASE_URL = 'https://calltracesniffer-production.up.railway.app';

// 分析单个交易
async function analyzeTx(txHash) {
  try {
    const response = await fetch(`${BASE_URL}/api/analyze`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ tx_hash: txHash }),
    });
    
    const result = await response.json();
    return result;
  } catch (error) {
    console.error('API 调用失败:', error);
    return { success: false, error: error.message };
  }
}

// 使用示例
async function example() {
  const result = await analyzeTx('0x5336739d401392b2d40043a9eac4396d45e1c2d9e606a62bd984b0a72f2931ff');
  
  if (result.success) {
    console.log('交易哈希:', result.tx_hash);
    console.log('Swap 数量:', result.stats.swaps_count);
    console.log('Transfer 数量:', result.stats.transfers_count);
    console.log('总 Gas:', result.stats.total_gas);
    
    // 获取 IR V1 JSON
    const irJson = result.ir_v1_json;
    console.log('IR V1 JSON:', irJson);
  } else {
    console.error('错误:', result.error);
  }
}

// 批量分析
async function analyzeBatch(txHashes) {
  // 创建 CSV 内容
  const csvContent = txHashes.join('\n');
  const blob = new Blob([csvContent], { type: 'text/csv' });
  const file = new File([blob], 'tx_hashes.csv', { type: 'text/csv' });
  
  const formData = new FormData();
  formData.append('file', file);
  
  try {
    const response = await fetch(`${BASE_URL}/api/analyze-batch`, {
      method: 'POST',
      body: formData,
    });
    
    const result = await response.json();
    return result;
  } catch (error) {
    console.error('批量分析失败:', error);
    return { success: false, error: error.message };
  }
}
```

### Node.js

```javascript
const axios = require('axios');

const BASE_URL = 'https://calltracesniffer-production.up.railway.app';

// 分析单个交易
async function analyzeTx(txHash) {
  try {
    const response = await axios.post(`${BASE_URL}/api/analyze`, {
      tx_hash: txHash
    }, {
      timeout: 300000  // 5 分钟超时
    });
    return response.data;
  } catch (error) {
    console.error('API 调用失败:', error.message);
    return { success: false, error: error.message };
  }
}

// 使用示例
(async () => {
  const result = await analyzeTx('0x5336739d401392b2d40043a9eac4396d45e1c2d9e606a62bd984b0a72f2931ff');
  console.log(JSON.stringify(result, null, 2));
})();
```

---

## ⚠️ 注意事项

### 1. 超时设置

由于 Playwright 需要加载页面和等待数据，API 请求可能需要较长时间（通常 30-120 秒）。请确保：

- **Python requests**: 设置 `timeout=300`（5 分钟）
- **JavaScript fetch**: 默认无超时限制，但建议使用 AbortController
- **curl**: 默认超时可能不够，使用 `--max-time 300`

### 2. 错误处理

所有 API 都返回统一的错误格式：

```json
{
  "success": false,
  "error": "错误描述信息"
}
```

常见错误：
- `交易哈希不能为空`: 未提供 tx_hash
- `无效的交易哈希格式`: tx_hash 格式不正确（必须以 0x 开头，66 字符）
- `无法提取交易数据`: BlockSec 页面无法访问或数据不存在
- `处理失败: ...`: 服务器内部错误

### 3. 批量分析限制

- 最多支持 **10 个交易** 批量分析
- 如果超过限制，会返回错误

### 4. 请求频率

Railway 免费计划对请求频率没有严格限制，但建议：
- 避免并发大量请求
- 单个请求完成后再进行下一个
- 批量分析时使用 `/api/analyze-batch` 而不是并发多个 `/api/analyze`

---

## 🔍 测试 API

### 使用 curl 快速测试

```bash
# 测试单个交易分析
curl -X POST https://calltracesniffer-production.up.railway.app/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"tx_hash": "0x5336739d401392b2d40043a9eac4396d45e1c2d9e606a62bd984b0a72f2931ff"}' \
  --max-time 300

# 测试获取 IR V1 JSON
curl -X POST https://calltracesniffer-production.up.railway.app/api/ir_parse \
  -H "Content-Type: application/json" \
  -d '{"tx_hash": "0x5336739d401392b2d40043a9eac4396d45e1c2d9e606a62bd984b0a72f2931ff"}' \
  --max-time 300
```

### 使用 Postman

1. 创建新请求
2. 方法: `POST`
3. URL: `https://calltracesniffer-production.up.railway.app/api/analyze`
4. Headers: `Content-Type: application/json`
5. Body (raw JSON):
```json
{
  "tx_hash": "0x5336739d401392b2d40043a9eac4396d45e1c2d9e606a62bd984b0a72f2931ff"
}
```

---

## 📊 响应数据结构

### 成功响应

```json
{
  "success": true,
  "tx_hash": "0x...",
  "ir_v1": {
    "tx_hash": "0x...",
    "rootTrace": { ... }
  },
  "ir_v1_json": "{ ... }",
  "stats": {
    "swaps_count": 2,
    "transfers_count": 5,
    "router_count": 3,
    "direct_count": 2,
    "virtual_count": 0,
    "total_gas": 150000
  }
}
```

### 错误响应

```json
{
  "success": false,
  "error": "错误描述"
}
```

---

## 🔗 相关文档

- [远程访问部署选项](./REMOTE_ACCESS_OPTIONS.md)
- [免费云平台部署](./FREE_CLOUD_DEPLOYMENT.md)
- [IR 规范文档](../development/IR_SPEC.md)

---

## 💡 快速分享给同事

你可以直接分享以下信息：

```
API 地址: https://calltracesniffer-production.up.railway.app

主要端点:
- POST /api/analyze - 分析单个交易
- POST /api/analyze-batch - 批量分析（最多10个）
- POST /api/ir_parse - 获取 IR V1 JSON
- POST /api/analyze-simulation - 分析模拟交易

Web UI: https://calltracesniffer-production.up.railway.app

详细文档: [分享此文档链接]
```
