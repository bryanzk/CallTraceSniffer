# BlockSec 交易分析工具

一个用于分析以太坊交易的Web应用，可以从BlockSec页面提取并分析交易的Swaps、Transfers和ExecutionTree信息。

## ✨ 功能特性

- 🔍 **单个交易分析**: 输入交易哈希，获取详细分析
- 📊 **批量分析**: 上传CSV文件，批量处理多个交易
- 📈 **实时统计**: 显示Swaps、Transfers、Gas消耗等统计信息
- 📝 **格式化输出**: 生成与test_cases.yaml格式一致的分析结果
- 💾 **结果下载**: 支持下载分析结果为文本文件
- 🐳 **Docker支持**: 完全容器化，无需配置环境

## 🚀 快速开始

### 方式1: Docker部署（推荐）

```bash
# 一键启动
chmod +x build_and_run.sh
./build_and_run.sh
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
│       ├── app.py              # Flask应用
│       ├── config.py           # 配置管理
│       ├── services/           # 业务逻辑层
│       │   ├── converter.py    # 数据转换服务
│       │   └── extractor.py   # 数据提取服务
│       ├── utils/              # 工具函数
│       │   └── address.py     # 地址处理
│       └── api/                # API路由
│           └── routes.py
├── scripts/                    # 脚本目录
│   ├── extract/                # 数据提取脚本
│   ├── process/                # 数据处理脚本
│   ├── parse/                  # 数据解析脚本
│   └── utils/                  # 工具脚本
├── tests/                      # 测试目录
│   ├── unit/                   # 单元测试
│   ├── integration/            # 集成测试
│   └── fixtures/               # 测试数据
├── docs/                       # 文档目录
│   ├── deployment/             # 部署文档
│   ├── development/            # 开发文档
│   └── setup/                  # 设置文档
├── config/                     # 配置目录
│   └── test_cases.yaml         # 测试用例参考
├── templates/                  # HTML模板
├── static/                     # 静态资源
├── Dockerfile                  # Docker配置
└── docker-compose.yml          # Docker Compose配置
```

## 📖 文档

- [Docker部署指南](docs/deployment/README_DOCKER.md) - 完整的Docker使用说明
- [快速开始](docs/deployment/QUICKSTART_DOCKER.md) - Docker快速上手指南
- [Web界面使用](docs/development/README_WEB.md) - Web应用使用说明
- [IR映射文档](docs/development/IR_MAPPING.md) - IR操作映射说明
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

分析结果格式与`test_cases.yaml`一致，包括：

- **Swaps**: 交换操作列表
- **ExecutionTree**: 执行树结构
- **Transfers**: 转账信息（Router/Direct/Virtual类型）
- **Gas统计**: 总Gas消耗和分类统计

## 🤝 贡献

欢迎提交Issue和Pull Request！

## 📄 许可证

[添加您的许可证]

## 🙏 致谢

- BlockSec - 提供交易数据源
- Playwright - 浏览器自动化
- Flask - Web框架

