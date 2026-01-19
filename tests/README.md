# 测试文档

## 测试结构

```
tests/
├── __init__.py
├── conftest.py                    # pytest配置和fixtures
├── fixtures/                      # 测试数据
│   ├── *.json                     # JSON测试数据
│   └── *.har                      # HAR文件
├── integration/                   # 集成测试
│   └── test_integration.py        # V1流程集成测试
├── unit/                          # 单元测试（27个文件）
│   ├── test_analysis_service*.py  # 分析服务测试
│   ├── test_api_*.py              # API测试
│   ├── test_ir_*.py               # IR解析测试
│   ├── test_simulation_*.py       # 模拟测试
│   └── test_*.py                  # 其他测试
└── README.md
```

## 测试文件列表

### 分析服务测试
| 文件 | 测试内容 |
|------|----------|
| `test_analysis_service.py` | AnalysisService 核心功能（12个测试） |
| `test_analysis_service_utils.py` | 工具函数测试（37个测试） |
| `test_analysis_service_fixture.py` | Fixture加载测试 |

### API测试
| 文件 | 测试内容 |
|------|----------|
| `test_api_routes_batch.py` | 批量API路由 |
| `test_api_flow_stats.py` | 流量统计API |
| `test_api_ir_parse.py` | IR解析API |
| `test_routes_helpers.py` | 路由辅助函数 |
| `test_validators.py` | 请求验证器 |
| `test_request_json_validation.py` | JSON验证 |

### IR解析测试
| 文件 | 测试内容 |
|------|----------|
| `test_ir_v1_blocksec.py` | BlockSec IR解析 |
| `test_ir_v1_blocksec_example.py` | IR解析示例 |
| `test_ir_v1_skeleton.py` | IR结构测试 |
| `test_ir_cases_smoke.py` | IR冒烟测试 |
| `test_ir_to_mermaid_api.py` | IR转Mermaid |
| `test_mermaid_dag.py` | Mermaid DAG生成 |
| `test_analyze_mermaid.py` | Mermaid分析 |

### 模拟测试
| 文件 | 测试内容 |
|------|----------|
| `test_simulation_api.py` | 模拟API |
| `test_simulation_params_placeholder.py` | 模拟参数 |
| `test_blocksec_simulation_service.py` | 模拟服务 |
| `test_simulate_and_analyze_*.py` | 模拟分析集成 |

### 其他测试
| 文件 | 测试内容 |
|------|----------|
| `test_format_address.py` | 地址格式化（9个测试） |
| `test_router_detection.py` | Router识别（7个测试） |
| `test_extractor_payload.py` | 数据提取 |
| `test_blocksec_extra_smoke.py` | BlockSec冒烟测试 |
| `test_smoke_flows.py` | 流程冒烟测试 |
| `test_smoke_unipool_dune.py` | Uniswap pool 查询冒烟测试 |

## 安装测试依赖

```bash
pip install -r requirements.txt
```

## 运行测试

### 运行所有测试

```bash
# 使用pytest
pytest

# 使用测试脚本
./run_tests.sh

# 详细输出
pytest -v
```

### 运行特定测试

```bash
# 运行特定文件
pytest tests/unit/test_analysis_service.py

# 运行特定类
pytest tests/unit/test_analysis_service.py::TestAnalysisService

# 运行特定函数
pytest tests/unit/test_analysis_service.py::test_analyze_tx_success_caches_and_builds_mermaid
```

### 按标记运行

```bash
# 只运行单元测试
pytest -m unit

# 只运行集成测试
pytest -m integration

# 只运行冒烟测试
pytest -m smoke
```

### 带覆盖率运行

```bash
# 生成覆盖率报告
pytest --cov=calltrace --cov-report=html

# 查看HTML报告
open htmlcov/index.html
```

## 测试统计

- **单元测试文件**: 27个
- **测试用例总数**: 149+
- **覆盖率目标**: >90%

### 测试分布

| 模块 | 测试数量 |
|------|----------|
| analysis_service | 50+ |
| API routes | 30+ |
| IR parsing | 25+ |
| Simulation | 20+ |
| Utils | 20+ |

## 编写新测试

1. 在相应的测试文件中添加新的测试方法
2. 使用 `pytest.fixture` 创建测试数据（在 conftest.py 中）
3. 遵循命名约定：`test_<功能描述>`
4. 使用断言验证预期结果

### 测试模板

```python
def test_function_name_expected_behavior(monkeypatch):
    """测试描述"""
    # Arrange - 准备测试数据
    input_data = {...}
    
    # Act - 执行被测函数
    result = function_under_test(input_data)
    
    # Assert - 验证结果
    assert result == expected_output
```

## 常见问题

### 导入错误
如果遇到导入错误，确保：
1. 在项目根目录运行测试
2. `src/` 已加入Python路径

### 测试失败
1. 检查测试数据是否正确
2. 验证被测试函数的实现是否改变
3. 查看详细错误信息：`pytest -v --tb=long`

## CI/CD

GitHub Actions配置在 `.github/workflows/tests.yml` 中，会在每次push和PR时自动运行测试。
