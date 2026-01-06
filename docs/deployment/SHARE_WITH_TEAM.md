# 分享给团队 - 快速指南

## 🎉 服务已部署！

**Web UI 地址**: https://calltracesniffer-production.up.railway.app

**API 地址**: https://calltracesniffer-production.up.railway.app

---

## 📱 使用方式

### 方式 1: Web 界面（最简单）

直接在浏览器中访问：
```
https://calltracesniffer-production.up.railway.app
```

然后：
1. 输入交易哈希
2. 点击"分析"
3. 查看结果并下载

### 方式 2: API 调用（适合集成到代码）

#### Python 示例

```python
import requests

# 分析单个交易
response = requests.post(
    "https://calltracesniffer-production.up.railway.app/api/analyze",
    json={"tx_hash": "0x你的交易哈希"},
    timeout=300
)
result = response.json()

if result.get("success"):
    print(f"Swap 数量: {result['stats']['swaps_count']}")
    print(f"Transfer 数量: {result['stats']['transfers_count']}")
    # 获取 IR V1 JSON
    ir_json = result['ir_v1_json']
else:
    print(f"错误: {result.get('error')}")
```

#### JavaScript 示例

```javascript
async function analyzeTx(txHash) {
  const response = await fetch(
    'https://calltracesniffer-production.up.railway.app/api/analyze',
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tx_hash: txHash })
    }
  );
  const result = await response.json();
  return result;
}

// 使用
const result = await analyzeTx('0x你的交易哈希');
console.log(result);
```

#### curl 示例

```bash
curl -X POST https://calltracesniffer-production.up.railway.app/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"tx_hash": "0x你的交易哈希"}' \
  --max-time 300
```

---

## 📋 主要 API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/analyze` | POST | 分析单个交易 |
| `/api/analyze-batch` | POST | 批量分析（最多10个） |
| `/api/ir_parse` | POST | 获取 IR V1 JSON |
| `/api/analyze-simulation` | POST | 分析模拟交易 |

---

## ⚠️ 重要提示

1. **超时设置**: API 请求可能需要 30-120 秒，请设置足够的超时时间（建议 300 秒）

2. **批量分析**: 最多支持 10 个交易，使用 CSV 文件格式：
   ```csv
   0x交易哈希1
   0x交易哈希2
   0x交易哈希3
   ```

3. **错误处理**: 所有 API 返回格式：
   ```json
   {
     "success": true/false,
     "tx_hash": "...",
     "ir_v1": {...},
     "stats": {...},
     "error": "错误信息（如果失败）"
   }
   ```

---

## 📚 详细文档

- **完整 API 文档**: [API_USAGE.md](./API_USAGE.md)
- **快速参考**: [API_QUICK_REFERENCE.md](./API_QUICK_REFERENCE.md)

---

## 🐛 遇到问题？

1. **检查网络连接**
2. **确认交易哈希格式正确**（0x 开头，66 字符）
3. **查看 API 返回的错误信息**
4. **联系技术支持**

---

## 💡 快速测试

使用以下测试交易哈希验证 API 是否正常工作：

```
0x5336739d401392b2d40043a9eac4396d45e1c2d9e606a62bd984b0a72f2931ff
```

测试命令：
```bash
curl -X POST https://calltracesniffer-production.up.railway.app/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"tx_hash": "0x5336739d401392b2d40043a9eac4396d45e1c2d9e606a62bd984b0a72f2931ff"}' \
  --max-time 300
```

如果返回 `{"success": true, ...}` 说明 API 正常工作！
