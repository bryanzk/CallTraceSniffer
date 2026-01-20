# BlockSec 交易分析工具 - Web界面

## 功能特性

- ✅ **单个交易分析**: 输入交易哈希，输出 IR V1 JSON
- ✅ **模拟TX**: 输入BlockSec模拟交易URL，解析模拟call trace
- ✅ **批量分析**: 上传CSV文件，批量处理多个交易（最多10个）
- ✅ **多交易支持Pool 检查**: 粘贴多笔交易哈希，判断是否命中 Uniswap Pool
- ✅ **实时统计**: 基于 IR V1 的 swap/transfer 数量统计
- ✅ **结果下载**: 支持下载 IR V1 JSON 文件

## 安装步骤

### 方式1: Docker部署（推荐，无需配置环境）

```bash
# 一键启动
chmod +x build_and_run.sh
./build_and_run.sh

# 或使用docker-compose
docker-compose up -d
```

详细说明请查看: [QUICKSTART_DOCKER.md](QUICKSTART_DOCKER.md)

### 方式2: 本地Python环境

1. **安装依赖**:
```bash
pip install -r requirements.txt
playwright install chromium
```

2. **启动应用**:
```bash
python app.py
```

3. **访问界面**:
打开浏览器访问: http://localhost:5001

**注意**: 如果遇到403错误，可能是端口5000被macOS AirPlay占用，应用已自动切换到端口5001

## 使用方法

### 单个交易分析

1. 在"单个交易"标签页中，输入交易哈希（0x开头，66个字符）
2. 点击"分析"按钮
3. 等待分析完成，查看结果
4. 可以点击"下载结果"保存 IR V1 JSON

### 批量分析

1. 准备CSV文件，格式如下：
```csv
0x0807fd45ea0116616ab5cb6b81dd1c395179713fd2465c1d610df14c0c404004
0x4036183ad1acab4c38a6d3027eb6e734fcc587477b6f26a109f1c6f49cbd5ec1
0x3d59ac33bcc54b76ba9000443983c0fa9b347423348231be1810d07aa724ae69
```

2. 在"批量分析"标签页中，点击"选择CSV文件"
3. 选择准备好的CSV文件
4. 点击"开始批量分析"
5. 查看每个交易的 IR V1 结果

### 单个TX模拟

1. 在"模拟TX"标签页中，输入BlockSec模拟交易URL（示例：
   `https://app.blocksec.com/explorer/tx/eth/0x...?...event=simulation&type=0`）
2. 点击"分析"按钮
3. 等待分析完成，查看结果
4. 可以点击"下载结果"保存 IR V1 JSON

**注意**: 如果页面被Cloudflare拦截，需要在浏览器登录并通过验证后再访问模拟URL。

### 多交易支持Pool 检查

1. 在“多交易支持Pool 检查”标签页中，换行粘贴交易哈希
2. 点击“查询”
3. 查看每笔交易是否命中 Uniswap Pool

**限制**: 仅支持以太坊主网；最多 10 条；只判断是否命中 Uniswap Pool；查询窗口为近 3 天。

## API接口

### POST /api/analyze
分析单个交易

**请求**:
```json
{
  "tx_hash": "0x..."
}
```

**响应**:
```json
{
  "success": true,
  "tx_hash": "0x...",
  "ir_v1": {...},
  "ir_v1_json": "{...}",
  "stats": {
    "swaps_count": 3,
    "transfers_count": 3,
    "router_count": 0,
    "direct_count": 0,
    "virtual_count": 0,
    "total_gas": 0
  }
}
```

### POST /api/analyze-batch
批量分析交易

**请求**: FormData with CSV file

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
      "ir_v1_json": "{...}",
      "stats": {...}
    },
    ...
  ]
}
```

### POST /api/tx-metrics-batch
批量交易指标（EigenPhi + Dune + RPC）

**请求**:
```json
{
  "tx_hashes": ["0x...", "0x..."]
}
```

**响应**:
```json
{
  "success": true,
  "block_start": 24182471,
  "block_end": 24278160,
  "results": [
    {
      "tx_hash": "0x...",
      "success": true,
      "blockNumber": 24278160,
      "gasUsed": 1700457,
      "builderTip": "0.000000000001700457",
      "builderTipPerGas": "0.000000000000000001",
      "coinbaseTransfer": "0.000034047305653313",
      "builderTipWithCT": "0.00003404730735377",
      "blockIndex": 128,
      "botAddress": "0x...",
      "builder": {
        "address": "0x...",
        "name": "builder-name-or-address"
      },
      "revenueEth": "0.002876356082165525",
      "revenueUsd": "9.1548550181512379531504185",
      "revenueUsdAll": "9.154855018151237953",
      "blockTxCount": 320
    }
  ]
}
```

### POST /api/analyze-simulation
分析模拟交易

**请求**:
```json
{
  "simulation_url": "https://app.blocksec.com/explorer/tx/eth/0x...?...event=simulation"
}
```

**响应**:
```json
{
  "success": true,
  "tx_hash": "0x...",
  "ir_v1": {...},
  "ir_v1_json": "{...}",
  "stats": {...}
}
```

### POST /api/download-result
下载 IR V1 JSON

**请求**:
```json
{
  "tx_hash": "0x...",
  "output_type": "ir_v1"
}
```

**响应**: JSON文件下载

### POST /api/ir_parse
返回 IR V1 JSON

**请求**:
```json
{
  "tx_hash": "0x..."
}
```

**响应**: 仅 IR V1 JSON

### POST /api/unipool/check
批量判断交易是否命中 Uniswap Pool

**请求**:
```json
{
  "tx_hashes": ["0x...", "0x..."]
}
```

**响应**:
```json
{
  "success": true,
  "results": [
    {
      "tx_hash": "0x...",
      "success": true,
      "has_uni_pool": true,
      "matched_pools": [],
      "error": null
    }
  ]
}
```

## 注意事项

1. **性能**: 每个交易分析需要约15-20秒（需要访问BlockSec页面并等待API响应）
2. **限制**: 批量分析最多支持10个交易
3. **Dune**: 使用 `/api/unipool/check` 或 `/api/tx-metrics-batch` 需要配置 `DUNE_API_KEY`
4. **EigenPhi**: 使用 `/api/tx-metrics-batch` 需要可访问 `storage.googleapis.com`
5. **RPC**: 使用 `/api/tx-metrics-batch` 需要配置 `ETH_RPC_URL`
6. **网络**: 需要能够访问BlockSec网站
7. **浏览器**: 使用Playwright的Chromium浏览器进行数据提取

## 技术栈

- **后端**: Flask (Python)
- **前端**: HTML + CSS + JavaScript (原生)
- **数据提取**: Playwright
- **Dune查询**: Dune API（Uniswap Pool 查询）
- **数据处理**: IR V1 解析与生成

## 故障排除

### 问题: 分析失败，提示"未能获取trace数据"
- 检查交易哈希是否正确
- 确认网络连接正常
- 确认交易在以太坊主网上

### 问题: Playwright相关错误
- 运行 `playwright install chromium` 安装浏览器
- 确认已安装所有依赖

### 问题: 端口被占用
- 修改 `app.py` 中的端口号（默认5000）
- 或使用 `lsof -ti:5000 | xargs kill` 释放端口
