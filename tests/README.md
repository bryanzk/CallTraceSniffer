# 单元测试文档

## 测试结构

```
tests/
├── __init__.py
├── conftest.py                    # pytest配置和fixtures
├── integration/
│   └── test_integration.py        # V1流程集成测试
├── unit/
│   ├── test_format_address.py     # 地址格式化测试
│   ├── test_ir_v1_case21.py       # V1对齐测试
│   ├── test_ir_v1_skeleton.py     # V1结构测试
│   ├── test_router_detection.py   # Router识别测试
│   └── test_simulation_api.py     # 模拟接口测试
└── README.md
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
pytest tests/unit/test_ir_v1_case21.py
pytest tests/integration/test_integration.py
```

### 运行特定测试类或函数

```bash
pytest tests/test_format_address.py::TestFormatAddress
pytest tests/test_format_address.py::TestFormatAddress::test_normal_address_truncation
```

### 带覆盖率运行

```bash
## 生成覆盖率报告
pytest --cov=calltrace --cov-report=html

# 查看HTML报告
open htmlcov/index.html
```

### 运行特定标记的测试

```bash
# 只运行单元测试
pytest -m unit

# 只运行集成测试
pytest -m integration

# 只运行冒烟测试
pytest -m smoke
```

## 测试覆盖范围

### 工具函数
- ✅ `format_address()` - 地址格式化（9个测试用例）
- ✅ `is_router_address()` - Router地址识别（7个测试用例）

### 数据提取/转换
- ✅ IR V1 解析与结构对齐（verified_ir_cases.json 对齐）
- ✅ IR V1 skeleton 输出顺序与字段规则

### 集成测试
- ✅ `process_tx_data()` - V1流程（端到端）

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
2. `src/` 已加入Python路径

### 测试失败
1. 检查测试数据是否正确
2. 验证被测试函数的实现是否改变
3. 查看详细错误信息：`pytest -v`

## CI/CD

GitHub Actions配置在`.github/workflows/tests.yml`中，会在每次push和PR时自动运行测试。
