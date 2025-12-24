# 单元测试文档

## 测试结构

```
tests/
├── __init__.py
├── conftest.py                    # pytest配置和fixtures
├── test_format_address.py         # 地址格式化测试
├── test_router_detection.py      # Router识别测试
├── test_transfer_extraction.py   # Transfer提取测试
├── test_swap_extraction.py        # Swap提取测试
├── test_execution_tree.py         # 执行树构建测试
├── test_output_formatting.py      # 输出格式化测试
├── test_integration.py            # 集成测试
└── fixtures/                      # 测试数据
    ├── sample_data_map.json
    └── sample_main_trace.json
```

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

### 运行特定测试文件

```bash
pytest tests/test_format_address.py
pytest tests/test_transfer_extraction.py
```

### 运行特定测试类或函数

```bash
pytest tests/test_format_address.py::TestFormatAddress
pytest tests/test_format_address.py::TestFormatAddress::test_normal_address_truncation
```

### 带覆盖率运行

```bash
# 生成覆盖率报告
pytest --cov=convert_to_test_case_v2 --cov=app --cov-report=html

# 查看HTML报告
open htmlcov/index.html
```

### 运行特定标记的测试

```bash
# 只运行单元测试
pytest -m unit

# 只运行集成测试
pytest -m integration
```

## 测试覆盖范围

### 工具函数
- ✅ `format_address()` - 地址格式化（9个测试用例）
- ✅ `is_router_address()` - Router地址识别（7个测试用例）

### 数据提取
- ✅ `extract_transfers_from_data()` - Transfer提取（20+个测试用例）
  - selector识别
  - method name识别
  - 参数变体支持
  - callData解析
  - Transfer类型分类（Router/Direct/Virtual）
  - Gas信息提取
  - 边界情况处理

- ✅ `extract_swaps_from_data()` - Swap提取（15+个测试用例）
  - method name识别
  - Form类型确定
  - 层级关系构建
  - 深度计算
  - 嵌套结构处理

### 数据处理
- ✅ `build_execution_tree_simplified()` - 执行树构建（15+个测试用例）
  - 单个/多个swap节点
  - Payload子节点
  - 嵌套结构
  - 节点信息
  - 边界情况

### 格式化
- ✅ `generate_test_case_format()` - 输出格式化（15+个测试用例）
  - 完整格式验证
  - 各部分格式
  - 统计信息
  - 边界情况

### 集成测试
- ✅ `process_tx_data()` - 完整流程（10+个测试用例）
  - 端到端数据流
  - 数据完整性
  - 统计准确性
  - 边界情况

## 测试覆盖率目标

- **行覆盖率**: >90%
- **分支覆盖率**: >85%
- **函数覆盖率**: 100%

## 编写新测试

1. 在相应的测试文件中添加新的测试方法
2. 使用`pytest.fixture`创建测试数据（在conftest.py中）
3. 遵循命名约定：`test_<功能描述>`
4. 使用断言验证预期结果

## 常见问题

### 导入错误
如果遇到导入错误，确保：
1. 在项目根目录运行测试
2. `convert_to_test_case_v2.py`和`app.py`在Python路径中

### 测试失败
1. 检查测试数据是否正确
2. 验证被测试函数的实现是否改变
3. 查看详细错误信息：`pytest -v`

## CI/CD

GitHub Actions配置在`.github/workflows/tests.yml`中，会在每次push和PR时自动运行测试。


