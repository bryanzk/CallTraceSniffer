# BlockSec 交易分析工具

一个用于分析以太坊交易的Web应用，可以从BlockSec页面提取并生成 IR V1 JSON。

## ✨ 功能特性

- 🔍 **单个交易分析**: 输入交易哈希，获取详细分析
- 🧪 **单个TX模拟**: 输入BlockSec模拟交易URL，解析模拟call trace
- 📊 **批量分析**: 上传CSV文件，批量处理多个交易
- 📈 **实时统计**: 基于 IR V1 的 swap/transfer 数量统计
- 📝 **IR V1 输出**: 生成 IR V1 JSON（与 IR 规范一致）
- 💾 **结果下载**: 支持下载 IR V1 JSON 文件
- 🐳 **Docker支持**: 完全容器化，无需配置环境

## 🚀 快速开始

### 方式1: Docker部署（推荐）

```bash
# 一键启动
chmod +x scripts/deploy/build_and_run.sh
./scripts/deploy/build_and_run.sh
```

详细说明: [QUICKSTART_DOCKER.md](docs/deployment/QUICKSTART_DOCKER.md)

### 方式2: 本地Python环境

```bash
# 安装依赖
pip install -r requirements.txt
playwright install chromium

# 启动应用
python run.py
```

访问: http://localhost:5001

## 📁 项目结构

```
CallTraceSniffer/
├── run.py                      # 应用入口点
├── src/                        # 源代码目录
│   └── calltrace/              # 主应用包
│       ├── app.py              # Flask应用入口
│       ├── config.py           # 配置管理
│       ├── api/                # API层
│       │   ├── routes.py       # 路由定义
│       │   └── validators.py   # 请求验证
│       ├── services/           # 业务逻辑层
│       │   ├── analysis_service.py  # 分析服务（核心）
│       │   ├── extractor.py         # 兼容层（转发至独立项目 blocksec-parser）
│       │   ├── ir_v1_blocksec.py    # BlockSec IR解析
│       │   ├── mermaid_dag.py       # Mermaid图生成
│       │   └── blocksec_simulation.py # 模拟服务
│       └── utils/              # 工具函数层
│           ├── address.py      # 地址处理
│           ├── analysis_utils.py # 分析工具函数
│           └── ir_format.py    # IR格式化
├── scripts/                    # 脚本目录
│   ├── deploy/                 # 部署脚本
│   ├── extract/                # 数据提取脚本
│   └── parse/                  # 数据解析脚本
├── tests/                      # 测试目录
│   ├── unit/                   # 单元测试（27个文件）
│   ├── integration/            # 集成测试
│   └── fixtures/               # 测试数据
├── docs/                       # 文档目录
│   ├── deployment/             # 部署文档
│   ├── development/            # 开发文档
│   └── setup/                  # 设置文档
├── config/                     # 配置目录
│   ├── test_cases.yaml         # 测试用例参考
│   └── secrets/                # 敏感配置（不提交）
├── templates/                  # HTML模板
├── static/                     # 静态资源
├── Dockerfile                  # Docker配置
└── docker-compose.yml          # Docker Compose配置
```

## 🔌 BlockSec 解析独立化

BlockSec 解析核心已拆分到独立项目 `blocksec-parser`（Library + CLI + HTTP）。
本仓库通过适配层保持 `calltrace.services.extractor.BlockSecExtractor` 兼容导入路径。
适配层通过 HTTP 调用 `blocksec-parser` 服务，地址由环境变量 `BLOCKSEC_PARSER_API_BASE_URL` 控制（默认 `http://127.0.0.1:4444`）。

## 📖 文档

### 部署文档
- [Docker部署指南](docs/deployment/README_DOCKER.md) - 完整的Docker使用说明
- [快速开始](docs/deployment/QUICKSTART_DOCKER.md) - Docker快速上手指南
- [远程访问部署选项](docs/deployment/REMOTE_ACCESS_OPTIONS.md) - 让同事远程访问服务的多种方式（Web UI + API）
- [免费云平台部署](docs/deployment/FREE_CLOUD_DEPLOYMENT.md) - Vercel、Cloudflare、Railway 等免费平台部署指南
- [Railway 部署指南](docs/deployment/RAILWAY_DEPLOYMENT.md) - Railway 平台详细部署说明
- [blocksec-parser 接入文档](docs/development/BLOCKSEC_PARSER_API_INTEGRATION.md) - 第三方 API 调用协议与重试策略
- [API 使用指南](docs/deployment/API_USAGE.md) - API 接口使用文档和代码示例

### 开发文档
- [Web界面使用](docs/development/README_WEB.md) - Web应用使用说明
- [数据流转文档](docs/development/DATA_FLOW.md) - 数据在各模块间的流转过程
- [IR规范文档](docs/development/IR_SPEC.md) - IR结构与字段规范（中英对照）
- [Gas记账规范](docs/development/GAS_ACCOUNTING.md) - Gas计算与展示规范
- [测试文档](tests/README.md) - 测试指南

## 🛠️ 技术栈

- **后端**: Flask (Python 3.11+)
- **前端**: HTML + CSS + JavaScript (原生)
- **数据提取**: Playwright
- **容器化**: Docker

## 📋 依赖

- Python 3.11+
- Flask 3.0.0
- Playwright 1.40.0
- Docker (可选，用于容器化部署)

## 🔧 开发

```bash
# 克隆仓库
git clone <repository-url>
cd CallTraceSniffer

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
playwright install chromium

# 运行开发服务器
python run.py
```

## 📝 使用示例

### 单个交易分析

1. 打开 http://localhost:5001
2. 在"单个交易"标签页输入交易哈希
3. 点击"分析"按钮
4. 查看结果并下载

### 批量分析

1. 准备CSV文件（每行一个交易哈希）
2. 在"批量分析"标签页上传CSV文件
3. 点击"开始批量分析"
4. 查看每个交易的结果

### 单个TX模拟

1. 打开 http://localhost:5001
2. 在"单个TX 模拟"标签页输入BlockSec模拟交易URL
3. 点击"分析"按钮
4. 查看结果并下载

## 🐳 Docker部署

### 构建镜像

```bash
docker build -t blocksec-analyzer:latest .
```

### 运行容器

```bash
docker run -d \
  --name blocksec-analyzer \
  -p 5001:5001 \
  --restart unless-stopped \
  blocksec-analyzer:latest
```

### 使用Docker Compose

```bash
docker-compose up -d
```

详细说明: [README_DOCKER.md](docs/deployment/README_DOCKER.md)

## 📊 输出格式

分析结果输出为 IR V1 JSON，规范见：
- `docs/development/IR_SPEC.md`

## 🤝 贡献

欢迎提交Issue和Pull Request！

## 📄 许可证

[添加您的许可证]

## 🙏 致谢

- BlockSec - 提供交易数据源
- Playwright - 浏览器自动化
- Flask - Web框架
