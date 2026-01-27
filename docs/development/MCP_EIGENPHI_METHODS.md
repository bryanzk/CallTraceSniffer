# EigenPhi MCP 服务器方法文档

本文档列出了 `MCP_EIGENPHI_SERVER` 提供的所有可用方法。

## 📋 方法列表

### 1. MEV 区块分析

#### `get_eigenphi_block_mev`
**描述**: 根据区块号查询 EigenPhi Block MEV 汇总

**参数**:
- `block_number` (必需, number): 区块号
- `list_url` (可选, string): 列表页 URL（内部调试参数）
- `tx0_hash` (可选, string): position 0 交易哈希（内部调试参数）

**返回**: 区块 MEV 汇总文本，包含：
- 区块号
- 类型汇总（套利、清算、三明治攻击等）
- 交易列表（每笔交易的利润、成本、收入）

**使用示例**:
```python
result = mcp_tool("get_eigenphi_block_mev", {"block_number": 24279007})
```

**在代码中的使用**:
- `src/calltrace/services/mev_block_service.py:465` - `MevBlockService._get_block_mev_data()`

---

### 2. MEV 交易分析

#### `get_eigenphi_tx_mev`
**描述**: 根据交易哈希查询 EigenPhi MEV 交易摘要

**参数**:
- `tx_hash` (必需, string): 交易哈希（0x 开头）
- `include_raw` (可选, boolean): 是否返回原始 JSON（默认 false）

**返回**: MEV 交易摘要，包含：
- Profit（利润）
- Cost（成本）
- Revenue（收入）
- Types（类型：Arbitrage、Liquidation、Sandwich 等）
- Chain ID、区块号、时间戳等

**使用示例**:
```python
result = mcp_tool("get_eigenphi_tx_mev", {
    "tx_hash": "0xce4226cd218e7638e1c6df65d028848618d97de8b2ca131a699f2afd6be0b803",
    "include_raw": False
})
```

---

#### `get_eigenphi_tx_mev_analysis`
**描述**: 根据交易哈希生成 EigenPhi MEV 策略分析

**参数**:
- `tx_hash` (必需, string): 交易哈希（0x 开头）
- `max_steps` (可选, number): 最多输出的关键动作条数（默认 8）

**返回**: MEV 策略分析，包含：
- 策略类型（Arbitrage、Liquidation、Sandwich 等）
- 策略组合描述
- 利润、成本、收入
- 关键动作流程（按顺序列出）

**使用示例**:
```python
result = mcp_tool("get_eigenphi_tx_mev_analysis", {
    "tx_hash": "0xce4226cd218e7638e1c6df65d028848618d97de8b2ca131a699f2afd6be0b803",
    "max_steps": 10
})
```

---

### 3. Token Flow Graph

#### `get_token_flow_graph`
**描述**: 获取交易的 Token Flow 资金流向图 (SVG)

**参数**:
- `tx_hash` (必需, string): 交易哈希（0x 开头）
- `chain` (可选, string): 链名称（默认 'ethereum'）

**返回**: SVG 格式的资金流向图

**使用示例**:
```python
result = mcp_tool("get_token_flow_graph", {
    "tx_hash": "0xce4226cd218e7638e1c6df65d028848618d97de8b2ca131a699f2afd6be0b803",
    "chain": "ethereum"
})
```

**在代码中的使用**:
- `src/calltrace/services/mev_block_service.py:482` - `MevBlockService._ensure_token_flow_svgs()`

---

### 4. 区块和交易信息

#### `get_block_by_number`
**描述**: 根据区块号获取区块详细信息

**参数**:
- `block_number` (必需, number): 区块号

**返回**: 区块详细信息

**使用示例**:
```python
result = mcp_tool("get_block_by_number", {"block_number": 24279007})
```

---

#### `get_latest_block`
**描述**: 获取以太坊最新区块号

**参数**: 无

**返回**: 最新区块号

**使用示例**:
```python
result = mcp_tool("get_latest_block", {})
```

---

#### `get_transaction`
**描述**: 根据交易哈希获取交易详情

**参数**:
- `tx_hash` (必需, string): 交易哈希（0x 开头）

**返回**: 交易详细信息

**使用示例**:
```python
result = mcp_tool("get_transaction", {
    "tx_hash": "0xce4226cd218e7638e1c6df65d028848618d97de8b2ca131a699f2afd6be0b803"
})
```

---

#### `get_balance`
**描述**: 查询以太坊地址的 ETH 余额

**参数**:
- `address` (必需, string): 以太坊地址（0x 开头）

**返回**: 地址的 ETH 余额

**使用示例**:
```python
result = mcp_tool("get_balance", {
    "address": "0x30a1b724c9dfe2e12a19ed84878312d199d1519e"
})
```

---

## 🔧 MCP 调用方式

### 在 Python 代码中调用

```python
def _call_mcp_tool(self, name: str, arguments: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """调用 MCP (Model Context Protocol) 工具并返回结果。"""
    request_payload = {
        "method": "tools/call", 
        "params": {
            "name": name, 
            "arguments": arguments
        }
    }
    
    result = subprocess.run(
        [self._mcp_server],
        input=json.dumps(request_payload),
        capture_output=True,
        text=True,
        timeout=self._timeout_seconds,
    )
    
    if result.returncode != 0:
        return None
    
    response = json.loads(result.stdout)
    if "error" in response:
        return None
    
    return response.get("result")
```

### 在 Cursor 中使用 MCP 工具

```python
# 使用 call_mcp_tool
result = call_mcp_tool(
    server="user-eigenphi-blockchain",
    toolName="get_eigenphi_tx_mev_analysis",
    arguments={
        "tx_hash": "0xce4226cd218e7638e1c6df65d028848618d97de8b2ca131a699f2afd6be0b803",
        "max_steps": 10
    }
)
```

---

## ⚙️ 配置

### 环境变量

- `MCP_EIGENPHI_SERVER`: MCP 服务器可执行文件路径
  - 默认值: `/Users/kezheng/Codes/CursorDeveloper/MEVAL/eigenphi-backend-go/bin/mcp-server`
  - 可通过 `.env` 文件或环境变量设置

- `MCP_TIMEOUT_SECONDS`: MCP 调用超时时间（秒）
  - 默认值: `120`
  - 可通过 `.env` 文件或环境变量设置

### 配置文件位置

- `src/calltrace/config.py`: 配置定义
- `.env`: 环境变量配置（如果存在）

---

## 📊 方法分类

### MEV 分析类
- `get_eigenphi_block_mev` - 区块 MEV 汇总
- `get_eigenphi_tx_mev` - 交易 MEV 摘要
- `get_eigenphi_tx_mev_analysis` - 交易 MEV 策略分析

### 可视化类
- `get_token_flow_graph` - Token Flow 图（SVG）

### 基础数据类
- `get_block_by_number` - 区块信息
- `get_latest_block` - 最新区块号
- `get_transaction` - 交易详情
- `get_balance` - 地址余额

---

## 🔗 相关代码

- `src/calltrace/services/mev_block_service.py` - MevBlockService 实现
- `src/calltrace/api/routes.py` - API 路由（使用 MevBlockService）
- `scripts/generate_mev_block_html.py` - HTML 生成脚本（直接调用 MCP）

---

## 📝 使用示例

### 示例 1: 获取区块 MEV 数据

```python
from calltrace.services.mev_block_service import MevBlockService

service = MevBlockService(
    mcp_server=config.MCP_EIGENPHI_SERVER,
    timeout_seconds=config.MCP_TIMEOUT_SECONDS
)

html, error = service.get_or_build_block(24279007, refresh=False)
```

### 示例 2: 分析交易策略

```python
# 在 Cursor 中使用
result = call_mcp_tool(
    server="user-eigenphi-blockchain",
    toolName="get_eigenphi_tx_mev_analysis",
    arguments={
        "tx_hash": "0xce4226cd218e7638e1c6df65d028848618d97de8b2ca131a699f2afd6be0b803",
        "max_steps": 10
    }
)
```

---

## 🚀 API 端点

项目中也提供了基于这些 MCP 方法的 API 端点：

- `POST /api/mev/block` - 获取 MEV 区块 HTML 片段
  - 参数: `block_number`, `refresh` (可选)
  - 返回: HTML 片段和查看器 URL
