# API 统计信息差别说明

本文档详细说明 `/api/analyze` 和 `/api/ir_parse` 两个端点在统计信息上的差别。

---

## 📊 核心差别

| 特性 | `/api/analyze` | `/api/ir_parse` |
|------|---------------|----------------|
| **返回格式** | JSON 对象 | 纯 JSON 字符串 |
| **包含 IR V1** | ✅ (对象格式) | ✅ (JSON 字符串) |
| **包含 IR V1 JSON** | ✅ | ✅ |
| **包含统计信息 (stats)** | ✅ | ❌ |
| **Content-Type** | `application/json` | `application/json` |
| **响应结构** | 结构化对象 | 纯 IR V1 JSON |

---

## 1️⃣ POST /api/analyze - 包含统计信息

### 返回结构

```json
{
  "success": true,
  "tx_hash": "0x5336739d401392b2d40043a9eac4396d45e1c2d9e606a62bd984b0a72f2931ff",
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

### 统计信息详解

`stats` 对象包含以下字段：

#### 1. `swaps_count` (整数)
- **含义**: IR V1 树中 swap 节点的总数量
- **计算方式**: 递归遍历 `rootTrace`，统计 `type == 'swap'` 的节点
- **来源**: `_count_ir_nodes(ir_v1.get('rootTrace'))`

#### 2. `transfers_count` (整数)
- **含义**: 所有 transfer 的总数量（包括 router、direct、virtual）
- **计算方式**: `router_count + direct_count + virtual_count`
- **来源**: `_compute_flow_counts(trace_data)`

#### 3. `router_count` (整数)
- **含义**: 通过 Router 的 transfer 数量
- **计算方式**: 识别涉及 Router 地址的 transfer，并合并匹配的流入/流出边
- **来源**: `_compute_flow_counts(trace_data)`

#### 4. `direct_count` (整数)
- **含义**: 直接 transfer 的数量（不经过 Router）
- **计算方式**: 识别不涉及 Router 的 transfer，包括从合并边中恢复的直接 transfer
- **来源**: `_compute_flow_counts(trace_data)`

#### 5. `virtual_count` (整数)
- **含义**: 虚拟 transfer 的数量（from == to）
- **计算方式**: 识别 `from` 和 `to` 地址相同的 transfer
- **来源**: `_compute_flow_counts(trace_data)`

#### 6. `total_gas` (整数)
- **含义**: 交易使用的总 Gas
- **计算方式**: 从 `trace_data.gasFlame` 中提取 "Actual Gas Used" 值
- **来源**: `_extract_total_gas(trace_data)`

### 代码实现

```python
# 位置: src/calltrace/api/routes.py (235-241行)

return jsonify({
    'success': True,
    'tx_hash': tx_hash,
    'ir_v1': analysis['ir_v1'],           # IR V1 对象
    'ir_v1_json': analysis['ir_v1_json'], # IR V1 JSON 字符串
    'stats': analysis['stats']            # ✅ 包含统计信息
})
```

---

## 2️⃣ POST /api/ir_parse - 不包含统计信息

### 返回结构

**直接返回 IR V1 JSON 字符串**，不包含任何包装：

```json
{
  "tx_hash": "0x5336739d401392b2d40043a9eac4396d45e1c2d9e606a62bd984b0a72f2931ff",
  "rootTrace": {
    "type": "swap",
    "address": "0x...",
    "amountIn": "...",
    "amountOut": "...",
    "callback": [...]
  }
}
```

**注意**: 
- ❌ 没有 `success` 字段
- ❌ 没有 `stats` 字段
- ❌ 没有外层包装对象
- ✅ 只有纯 IR V1 JSON

### 代码实现

```python
# 位置: src/calltrace/api/routes.py (445行)

return app.response_class(analysis['ir_v1_json'], mimetype='application/json')
```

**关键点**: 
- 虽然内部也调用了 `process_tx_data()`（会生成 stats），但返回时**只提取了 `ir_v1_json`**
- stats 信息被**丢弃**，不会返回给客户端

---

## 🔍 内部处理流程对比

### 两个端点都执行相同的处理

```python
# 两个端点都会执行：
extractor = BlockSecExtractor()
result = asyncio.run(extractor.extract_blocksec_data(tx_hash))
trace_data = result.get('trace_data')
analysis = process_tx_data(trace_data, tx_hash)  # ✅ 都会生成 stats
```

`process_tx_data()` 函数**总是会生成 stats**，无论哪个端点调用：

```python
# 位置: src/calltrace/api/routes.py (170-192行)

def process_tx_data(trace_data, tx_hash=None):
    """处理交易数据并生成分析结果"""
    if not trace_data:
        return None
    
    ir_v1 = build_blocksec_ir(trace_data, tx_hash)
    ir_v1_json = _serialize_ir_payload(ir_v1, tx_hash)
    swaps_count, _ = _count_ir_nodes(ir_v1.get('rootTrace'))
    transfers_count, router_count, direct_count, virtual_count = _compute_flow_counts(trace_data)
    total_gas = _extract_total_gas(trace_data)
    
    return {
        'ir_v1': ir_v1,
        'ir_v1_json': ir_v1_json,
        'stats': {  # ✅ stats 总是会被生成
            'swaps_count': swaps_count,
            'transfers_count': transfers_count,
            'router_count': router_count,
            'direct_count': direct_count,
            'virtual_count': virtual_count,
            'total_gas': total_gas
        },
    }
```

### 差别在于返回内容

| 端点 | 返回内容 | 说明 |
|------|---------|------|
| `/api/analyze` | 完整的 `analysis` 对象 | 包含 `ir_v1`、`ir_v1_json` 和 `stats` |
| `/api/ir_parse` | 仅 `analysis['ir_v1_json']` | 只返回 IR V1 JSON 字符串，丢弃 `stats` |

---

## 📝 使用场景对比

### 使用 `/api/analyze` 的场景

✅ **需要统计信息时**
- 需要知道 swap 数量、transfer 数量
- 需要分析 Gas 使用情况
- 需要了解流量类型分布（router/direct/virtual）

**示例**:
```python
response = requests.post(f"{BASE_URL}/api/analyze", json={"tx_hash": tx_hash})
result = response.json()

if result['success']:
    print(f"Swap 数量: {result['stats']['swaps_count']}")
    print(f"Transfer 数量: {result['stats']['transfers_count']}")
    print(f"总 Gas: {result['stats']['total_gas']}")
    # 同时可以访问 IR V1
    ir_v1 = result['ir_v1']
```

### 使用 `/api/ir_parse` 的场景

✅ **只需要 IR V1 JSON 时**
- 只需要 IR V1 格式的数据
- 不需要统计信息
- 需要直接保存或处理 IR V1 JSON

**示例**:
```python
response = requests.post(f"{BASE_URL}/api/ir_parse", json={"tx_hash": tx_hash})
ir_v1_json = response.text  # 直接是 JSON 字符串

# 保存到文件
with open('ir_v1.json', 'w') as f:
    f.write(ir_v1_json)

# 或解析为对象
import json
ir_v1 = json.loads(ir_v1_json)
```

---

## 💡 性能考虑

### 计算成本

两个端点**计算成本相同**，因为：
1. 都调用 `process_tx_data()`，会计算所有 stats
2. `/api/ir_parse` 虽然不返回 stats，但**仍然会计算**（只是丢弃结果）

### 响应大小

| 端点 | 响应大小 | 说明 |
|------|---------|------|
| `/api/analyze` | 较大 | 包含 IR V1 对象、JSON 字符串和 stats |
| `/api/ir_parse` | 较小 | 只包含 IR V1 JSON 字符串 |

**建议**: 如果只需要 IR V1 JSON，使用 `/api/ir_parse` 可以减少网络传输。

---

## 🔄 缓存机制

两个端点都使用相同的缓存：

```python
extracted_data_cache[tx_hash] = {
    'trace_data': trace_data,
    'analysis': analysis  # 包含 stats
}
```

**缓存命中时的行为**:

- `/api/analyze`: 从缓存中获取完整的 `analysis`，返回所有内容
- `/api/ir_parse`: 从缓存中获取 `analysis`，但只返回 `ir_v1_json`

---

## 📊 完整对比表

| 特性 | `/api/analyze` | `/api/ir_parse` |
|------|---------------|----------------|
| **端点路径** | `/api/analyze` | `/api/ir_parse` |
| **请求方法** | POST | POST |
| **请求体** | `{"tx_hash": "0x..."}` | `{"tx_hash": "0x..."}` |
| **内部处理** | 相同（都调用 `process_tx_data()`） | 相同 |
| **计算 stats** | ✅ 是 | ✅ 是（但不返回） |
| **返回格式** | JSON 对象 | JSON 字符串 |
| **返回字段** | `success`, `tx_hash`, `ir_v1`, `ir_v1_json`, `stats` | 纯 IR V1 JSON |
| **stats 字段** | ✅ 包含 | ❌ 不包含 |
| **响应大小** | 较大 | 较小 |
| **适用场景** | 需要统计信息 | 只需要 IR V1 JSON |

---

## 🎯 选择建议

### 使用 `/api/analyze` 如果：
- ✅ 需要统计信息（swap 数量、transfer 数量、Gas 等）
- ✅ 需要结构化的响应（包含 success 状态）
- ✅ 需要同时获取 IR V1 对象和 JSON 字符串

### 使用 `/api/ir_parse` 如果：
- ✅ 只需要 IR V1 JSON 数据
- ✅ 不需要统计信息
- ✅ 希望减少响应大小
- ✅ 需要直接保存 IR V1 JSON 到文件

---

## 📚 相关文档

- [API 使用指南](./API_USAGE.md) - 完整的 API 使用说明
- [API 解析逻辑](./API_PARSING_LOGIC.md) - 解析逻辑详解
- [IR 规范文档](../development/IR_SPEC.md) - IR V1 格式规范

---

## 🔍 代码位置

- `/api/analyze`: `src/calltrace/api/routes.py` (198-244行)
- `/api/ir_parse`: `src/calltrace/api/routes.py` (405-447行)
- `process_tx_data()`: `src/calltrace/api/routes.py` (170-192行)
