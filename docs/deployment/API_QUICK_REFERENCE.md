# API 快速参考

## 🌐 生产环境地址

```
https://calltracesniffer-production.up.railway.app
```

## 📋 主要 API 端点

### 1. 分析单个交易

```bash
POST /api/analyze
Content-Type: application/json

{
  "tx_hash": "0x5336739d401392b2d40043a9eac4396d45e1c2d9e606a62bd984b0a72f2931ff"
}
```

### 2. 批量分析（最多10个）

```bash
POST /api/analyze-batch
Content-Type: multipart/form-data

file: tx_hashes.csv (每行一个交易哈希)
```

### 3. 获取 IR V1 JSON

```bash
POST /api/ir_parse
Content-Type: application/json

{
  "tx_hash": "0x..."
}
```

### 4. 分析模拟交易

```bash
POST /api/analyze-simulation
Content-Type: application/json

{
  "simulation_url": "https://app.blocksec.com/explorer/tx/eth/0x...?event=simulation"
}
```

## 💻 快速示例

### Python

```python
import requests

BASE_URL = "https://calltracesniffer-production.up.railway.app"

# 分析交易
response = requests.post(
    f"{BASE_URL}/api/analyze",
    json={"tx_hash": "0x5336739d401392b2d40043a9eac4396d45e1c2d9e606a62bd984b0a72f2931ff"},
    timeout=300
)
result = response.json()
print(result)
```

### JavaScript

```javascript
const BASE_URL = 'https://calltracesniffer-production.up.railway.app';

fetch(`${BASE_URL}/api/analyze`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    tx_hash: '0x5336739d401392b2d40043a9eac4396d45e1c2d9e606a62bd984b0a72f2931ff'
  })
})
.then(res => res.json())
.then(data => console.log(data));
```

### curl

```bash
curl -X POST https://calltracesniffer-production.up.railway.app/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"tx_hash": "0x5336739d401392b2d40043a9eac4396d45e1c2d9e606a62bd984b0a72f2931ff"}' \
  --max-time 300
```

## ⚠️ 注意事项

- **超时**: 请求可能需要 30-120 秒，请设置足够的超时时间
- **批量限制**: 最多支持 10 个交易
- **错误处理**: 所有 API 返回 `{"success": true/false, ...}` 格式

## 📚 详细文档

完整 API 文档请参考: [API_USAGE.md](./API_USAGE.md)
