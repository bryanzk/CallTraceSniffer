# 可提交的文件清单

## ✅ 核心功能文件（建议提交）

### 测试相关（重要）
- `tests/` - IR V1 测试套件
- `pytest.ini` - pytest配置文件
- `run_tests.sh` - 测试运行脚本
- `.github/workflows/tests.yml` - CI/CD配置

### 配置文件
- `.gitignore` - 已修改，添加了测试相关忽略规则
- `requirements.txt` - 已修改，添加了pytest依赖

## ⚠️ 其他文件（根据需求决定）

### 数据处理脚本（可能是临时脚本）
- `scripts/extract/*`
- `scripts/parse/*`
- `scripts/utils/compare_blocksec_tenderly.py`

### 文档和报告
- `detailed_all_cases_report.md` - 分析报告
- `交易路径优化和执行编排的设计方案.md` - 设计文档
- `交易路径优化和执行编排的设计方案.pdf` - PDF文档

### 其他
- `.gitignore.docker` - Docker相关（可能不需要）
- `start_web.sh` - Web启动脚本（如果已包含在Docker中可能不需要）

## 📋 推荐提交命令

### 只提交测试相关（推荐）
```bash
git add tests/
git add pytest.ini
git add run_tests.sh
git add .github/workflows/tests.yml
git add .gitignore
git add requirements.txt
git commit -m "添加IR V1测试套件

- 覆盖V1解析与API流程
- 配置pytest和覆盖率工具
- 添加CI/CD测试流程
- 更新依赖和.gitignore"
```

### 提交所有核心文件
```bash
# 先添加测试相关
git add tests/ pytest.ini run_tests.sh .github/ .gitignore requirements.txt

# 如果需要，也可以添加其他脚本
git add scripts/extract scripts/parse scripts/utils/compare_blocksec_tenderly.py

git commit -m "添加单元测试和数据处理脚本"
```

## 🚫 不建议提交的文件

根据`.gitignore`，以下文件类型会被忽略：
- `*.json` - JSON数据文件
- `*.yaml` - YAML数据文件（除了test_cases.yaml）
- `*.md` - Markdown文档（除了README）
- `*.pdf` - PDF文件
- `__pycache__/` - Python缓存
- `*.pyc` - 编译的Python文件
