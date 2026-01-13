# 外部依赖数据文档

## 📋 概述

本文档记录项目中依赖的所有外部给定数据，包括硬编码的地址、配置常量、外部服务依赖等。

## 🔍 依赖分类

### 1. 外部服务依赖

| 服务 | 文件 | 用途 | 影响范围 |
|------|------|------|----------|
| BlockSec API | `blocksec_simulation.py` | 模拟交易 | 模拟功能 |
| BlockSec 页面 | `extractor.py` | 数据抓取 | 核心功能 |

#### BlockSec API 端点

**文件**: `src/calltrace/services/blocksec_simulation.py`

```python
BLOCKSEC_API_BASE = "https://app.blocksec.com/api/v1"
BLOCKSEC_SIMULATION_ENDPOINT = f"{BLOCKSEC_API_BASE}/tx/simulation"
BLOCKSEC_SIM_TRACE_ENDPOINT = f"{BLOCKSEC_API_BASE}/simulation/tx/trace"
BLOCKSEC_SIM_BALANCE_ENDPOINT = f"{BLOCKSEC_API_BASE}/simulation/tx/balance-change"
BLOCKSEC_SIM_BASIC_ENDPOINT = f"{BLOCKSEC_API_BASE}/simulation/tx/basic-info"
```

#### BlockSec 页面 URL

**文件**: `src/calltrace/services/extractor.py`

```python
url = f"https://app.blocksec.com/explorer/tx/eth/{tx_hash}/"
```

---

### 2. 认证/Cookie 依赖

| 文件 | 路径 | 环境变量 | 必需性 |
|------|------|----------|--------|
| Cookie 文件 | `blocksec_cookies.json` | `BLOCKSEC_COOKIE_FILE` | 模拟功能必需 |

**文件**: `src/calltrace/services/blocksec_simulation.py`

```python
def resolve_cookie_file() -> Path:
    root = Path(__file__).resolve().parents[3]
    cookie_file = os.getenv("BLOCKSEC_COOKIE_FILE", str(root / "blocksec_cookies.json"))
    return Path(cookie_file)
```

**影响**: 
- 模拟交易 API 需要有效的 BlockSec cookies
- Cookie 失效时返回 403 错误

---

### 3. 硬编码的以太坊地址

#### 3.1 事件 Topic（协议标准）

**文件**: `src/calltrace/services/ir_v1_blocksec.py`

| 常量 | 值 | 描述 |
|------|-----|------|
| `TOPIC_V3` | `0xc42079f94...` | Uniswap V3 Swap 事件 |
| `TOPIC_V4` | `0x40e9cecb9...` | Uniswap V4 Swap 事件 |
| `TOPIC_V2` | `0xd78ad95fa...` | Uniswap V2 Swap 事件 |
| `TOPIC_TRANSFER` | `0xddf252ad1...` | ERC20 Transfer 事件 |

```python
TOPIC_V3 = "0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67"
TOPIC_V4 = "0x40e9cecb9f5f1f1c5b9c97dec2917b7ee92e57ba5563708daca94dd84ad7112f"
TOPIC_V2 = "0xd78ad95fa46c994b6551d0da85fc275fe613ce37657fb8d5e3d130840159d822"
TOPIC_TRANSFER = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
```

**性质**: 这些是以太坊协议标准，不会改变。

#### 3.2 特定合约地址

**文件**: `src/calltrace/services/ir_v1_blocksec.py`

```python
V4_POOL_MANAGER = "0x000000000004444c5dc75cb358380d2e3de08a90"
```

**影响**: 用于识别 Uniswap V4 Pool Manager 合约

#### 3.3 Token 精度映射

**文件**: `src/calltrace/services/ir_v1_blocksec.py`

```python
TOKEN_DECIMALS = {
    "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48": 6,   # USDC
    "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2": 18,  # WETH
    "0x2260fac5e5542a773aa44fbcfedf7c193bc2c599": 8,   # WBTC
    "0xdac17f958d2ee523a2206206994597c13d831ec7": 6,   # USDT
    "0xa9d54f37ebb99f83b603cc95fc1a5f3907aaccfd": 18,  # 自定义Token
}
```

**影响**: 金额精度计算

#### 3.4 Pool 地址规范化

**文件**: `src/calltrace/services/ir_v1_blocksec.py`

```python
POOL_ID_CANONICAL = {
    "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640": "0x88e6A0c2dDD26FEEb64F039a2c41296FcB3f5640",
    # ... 16个池地址映射
}
```

**影响**: Pool ID 格式统一

#### 3.5 特定交易覆盖

**文件**: `src/calltrace/services/ir_v1_blocksec.py`

```python
ROOT_RECIPIENT_OVERRIDES = {
    "0xe42c7f10664571e96b425333a7a06fae1de65dd30eb871d84ceb559cceed00a6": "0xc2fe164d2cfcfeb6164242b807c57c691f7cfb37",
    "0xe8e213f71cad840d681b6ae34870e7f75518c6d66ebdbc2500d0e49b9112a873": "0x60a8df372371124aeaf292b338fbbc7187c91bed",
}

AMOUNT_OVERRIDES = {
    "0x34d13a12d4a860ee931cbfafcc016825eeabcec64e82b09c54da7646f8c85b15": {
        # 特定池的金额覆盖
    }
}
```

**影响**: 针对特定交易的硬编码修正

---

### 4. 配置文件依赖

**文件**: `src/calltrace/config.py`

#### 4.1 Router 地址

```python
ROUTER_ADDRESSES: List[str] = [
    '0x00000000009e50a7ddb7a7b0e2ee6604fd120e49',  # 0e49 as Router
    '0xe6f5c83b9d2005bf14333d7e48d3002fff4c93a7',
]
```

**影响**: 流量分类（Router/Direct/Virtual）

#### 4.2 Token 地址

```python
WETH: str = '0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2'
USDC: str = '0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48'
```

**影响**: 
- WETH 判断 (`tokenInIsWETH`, `tokenOutIsWETH`)
- 金额编码

#### 4.3 其他配置

```python
TRANSFER_SELECTOR: str = '0xa9059cbb'
BLOCKSEC_BASE_URL: str = 'https://blocksec.com'
MAX_BATCH_SIZE: int = 10
REQUEST_TIMEOUT: int = 30000
```

---

### 5. 环境变量依赖

| 变量 | 默认值 | 文件 | 用途 |
|------|--------|------|------|
| `FLASK_ENV` | `development` | `config.py` | Flask 环境 |
| `PORT` | `5001` | `config.py` | 服务端口 |
| `DEBUG` | `True` | `config.py` | 调试模式 |
| `HOST` | `0.0.0.0` | `config.py` | 服务地址 |
| `USE_FIXTURE` | `""` | `analysis_service.py` | 测试模式 |
| `FIXTURE_PATH` | `tests/fixtures/...json` | `analysis_service.py` | Fixture 路径 |
| `BLOCKSEC_COOKIE_FILE` | `blocksec_cookies.json` | `blocksec_simulation.py` | Cookie 文件 |

---

### 6. 测试 Fixture 依赖

**文件**: `src/calltrace/services/analysis_service.py`

```python
default_path = root / "tests/fixtures/0xe42c7f10664571e96b425333a7a06fae1de65dd30eb871d84ceb559cceed00a6_blocksec_trace.json"
```

**影响**: 测试模式下使用的默认 Fixture 文件

---

## 📊 依赖影响分析

### 高影响依赖

| 依赖 | 影响 | 失效后果 |
|------|------|----------|
| BlockSec 页面 | 核心功能 | 无法提取数据 |
| BlockSec cookies | 模拟功能 | 模拟 API 返回 403 |
| ROUTER_ADDRESSES | 流量统计 | 分类错误 |

### 中影响依赖

| 依赖 | 影响 | 失效后果 |
|------|------|----------|
| TOKEN_DECIMALS | 金额显示 | 精度错误 |
| POOL_ID_CANONICAL | ID 格式 | 格式不一致 |
| WETH 地址 | WETH 判断 | 字段错误 |

### 低影响依赖

| 依赖 | 影响 | 失效后果 |
|------|------|----------|
| 事件 Topic | 协议标准 | 不会改变 |
| 覆盖映射 | 特定交易 | 仅影响特定交易 |

---

## 🔧 维护建议

### 1. 需要定期更新的依赖

- **BlockSec cookies**: 定期更新以保持模拟功能
- **ROUTER_ADDRESSES**: 新增 Router 时需要更新
- **TOKEN_DECIMALS**: 新增 Token 时需要更新

### 2. 可配置化建议

#### 优先级高

1. **ROUTER_ADDRESSES** → 移到外部配置文件
   ```yaml
   # config/routers.yaml
   routers:
     - address: "0x..."
       name: "Uniswap Router"
   ```

2. **TOKEN_DECIMALS** → 支持动态查询
   ```python
   # 从链上查询或外部API获取
   async def get_token_decimals(token_address):
       pass
   ```

#### 优先级中

3. **POOL_ID_CANONICAL** → 移到外部配置文件
4. **覆盖映射** → 移到外部配置文件

### 3. 建议的配置文件结构

```
config/
├── app.yaml           # 应用配置（端口、环境等）
├── routers.yaml       # Router 地址列表
├── tokens.yaml        # Token 配置（地址、精度）
├── pools.yaml         # Pool 配置（ID规范化）
├── overrides.yaml     # 特定交易覆盖
└── secrets/
    └── blocksec_cookies.json
```

---

## 📋 依赖文件清单

### 源代码中的硬编码

| 文件 | 依赖类型 | 数量 |
|------|----------|------|
| `ir_v1_blocksec.py` | 地址/Topic/覆盖 | 50+ |
| `config.py` | 配置常量 | 10+ |
| `blocksec_simulation.py` | API 端点 | 5 |
| `extractor.py` | URL 模板 | 2 |
| `analysis_service.py` | Fixture 路径 | 1 |

### 外部文件依赖

| 文件 | 用途 | 必需性 |
|------|------|--------|
| `blocksec_cookies.json` | BlockSec 认证 | 模拟功能必需 |
| `tests/fixtures/*.json` | 测试数据 | 测试模式必需 |

---

## 🚨 风险提示

1. **BlockSec 服务不可用**
   - 影响: 核心功能完全不可用
   - 缓解: 实现备用数据源或缓存

2. **Cookie 失效**
   - 影响: 模拟功能不可用
   - 缓解: 自动检测并提示更新

3. **Router 地址不完整**
   - 影响: 流量统计不准确
   - 缓解: 支持动态配置

4. **新 Token 未收录**
   - 影响: 金额精度错误
   - 缓解: 从链上动态查询精度

5. **协议升级**
   - 影响: 新版本协议可能无法识别
   - 缓解: 定期更新 Topic 常量
