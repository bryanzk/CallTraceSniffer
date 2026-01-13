# 开发文档

## 📚 文档索引

### 核心文档
- [Web界面使用说明](README_WEB.md) - Web应用使用说明
- [数据流转文档](DATA_FLOW.md) - 数据在各模块间的流转过程（包含数据流图）
- [IR规范文档](IR_SPEC.md) - IR结构与字段规范（中英对照）
- [IR V1 解析流程](IR_V1_FLOW.md) - BlockSec→IR V1 标准流程（中英对照）
- [Gas记账规范](GAS_ACCOUNTING.md) - Gas计算与展示规范
- [测试文档](../../tests/README.md) - 单元测试和集成测试指南

### 重构文档
- [代码审查报告](ANALYSIS_SERVICE_REVIEW.md) - analysis_service.py 代码审查
- [测试覆盖报告](ANALYSIS_SERVICE_TEST_COVERAGE.md) - 测试覆盖情况
- [重构1.1: 配置注入](REFACTOR_1_1_CONFIG_INJECTION.md) - 注入配置对象
- [重构1.2: Extractor注入](REFACTOR_1_2_EXTRACTOR_INJECTION.md) - 修复直接类调用
- [重构1.3: 延迟导入](REFACTOR_1_3_LAZY_CONFIG_IMPORT.md) - 延迟导入全局配置
- [重构2.1: Fixture加载器](REFACTOR_2_1_FIXTURE_LOADER.md) - 提取Fixture加载器
- [重构4.1: 工具函数提取](REFACTOR_4_1_EXTRACT_UTILS.md) - 提取工具函数到独立模块

## 项目结构

项目采用分层架构设计，主要代码位于 `src/calltrace/` 目录：

```
src/calltrace/
├── app.py                  # Flask应用入口
├── config.py               # 配置管理
├── api/                    # API层（路由和验证）
│   ├── routes.py           # 路由定义
│   └── validators.py       # 请求验证
├── services/               # 业务逻辑层
│   ├── analysis_service.py # 分析服务（核心）
│   │   ├── AnalysisService # 分析服务类
│   │   ├── ServiceResult   # 服务结果数据类
│   │   ├── RouterConfig    # 路由器配置
│   │   └── FixtureLoader   # Fixture加载器
│   ├── extractor.py        # BlockSec数据提取服务
│   ├── ir_v1_blocksec.py   # BlockSec IR解析
│   ├── ir_v1_tenderly.py   # Tenderly IR解析
│   ├── mermaid_dag.py      # Mermaid图生成
│   └── blocksec_simulation.py # 模拟服务
├── utils/                  # 工具函数层
│   ├── address.py          # 地址处理工具
│   ├── analysis_utils.py   # 分析工具函数
│   │   ├── count_ir_nodes()      # 统计IR节点
│   │   ├── extract_total_gas()   # 提取Gas
│   │   ├── extract_transfer_edges() # 提取转账边
│   │   ├── compute_flow_counts() # 计算流量统计
│   │   └── process_tx_data()     # 处理交易数据
│   └── ir_format.py        # IR格式化工具
└── models/                 # 数据模型层
    └── __init__.py
```

### 分层说明

| 层级 | 目录 | 职责 |
|------|------|------|
| API层 | `api/` | 处理HTTP请求、验证、响应 |
| 服务层 | `services/` | 业务逻辑、数据处理 |
| 工具层 | `utils/` | 纯函数工具、通用逻辑 |
| 模型层 | `models/` | 数据结构定义 |

### 依赖关系

```
API层 (routes.py)
    ↓
服务层 (analysis_service.py, extractor.py)
    ↓
工具层 (analysis_utils.py, address.py)
```

## 开发环境设置

1. 克隆仓库
2. 创建虚拟环境：`python3 -m venv venv`
3. 激活虚拟环境：`source venv/bin/activate`
4. 安装依赖：`pip install -r requirements.txt`
5. 安装 Playwright：`playwright install chromium`

## 运行开发服务器

```bash
python run.py
```

服务器将在 http://localhost:5001 启动

## 运行测试

```bash
# 运行所有测试
./run_tests.sh

# 运行单元测试
pytest tests/unit/ -v

# 运行冒烟测试
pytest -m smoke -v

# 带覆盖率运行
pytest --cov=calltrace --cov-report=html
```

## 代码质量

项目遵循以下原则：

- **依赖注入**: 通过构造函数注入依赖，提高可测试性
- **分层隔离**: API层、服务层、工具层职责分明
- **单一职责**: 每个模块/函数只负责一件事
- **向后兼容**: 重构时保持API兼容性
