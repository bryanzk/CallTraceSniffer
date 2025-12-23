# 重构实施计划

## 🎯 目标

将项目重构为符合Python最佳实践的标准结构，提高可维护性和可扩展性。

## 📊 当前 vs 目标结构对比

### 当前结构（扁平化）
```
CallTraceSniffer/
├── app.py                    # Flask应用
├── convert_to_test_case_v2.py
├── extract_*.py (5个文件)
├── process_*.py (2个文件)
├── parse_*.py (1个文件)
├── *.md (8个文档)
├── *.sh (4个脚本)
└── tests/
```

### 目标结构（模块化）
```
CallTraceSniffer/
├── src/calltrace/           # 核心应用代码
├── scripts/                 # 数据处理脚本
├── docs/                    # 文档
├── config/                  # 配置
└── tests/                   # 测试
```

## 🚀 快速开始（最小改动方案）

如果不想大规模重构，可以采用**渐进式改进**：

### 方案A: 最小改动（推荐先实施）

只做必要的组织，不改变代码结构：

```bash
# 1. 创建scripts目录，移动数据处理脚本
mkdir -p scripts/{extract,process,parse}
mv extract_*.py scripts/extract/
mv process_*.py scripts/process/
mv parse_*.py scripts/parse/

# 2. 创建docs目录，移动文档（保留README.md）
mkdir -p docs
mv README_*.md QUICKSTART_*.md DOCKER_*.md GITHUB_*.md SET_*.md docs/

# 3. 创建config目录
mkdir -p config
mv test_cases.yaml config/

# 4. 保持核心代码在根目录（app.py, convert_to_test_case_v2.py）
# 这样改动最小，风险最低
```

### 方案B: 完整重构（长期目标）

按照 `ARCHITECTURE_RECOMMENDATIONS.md` 中的建议进行完整重构。

## 📋 实施步骤（方案A - 最小改动）

### 步骤1: 组织脚本（5分钟）

```bash
# 创建目录
mkdir -p scripts/{extract,process,parse,utils}

# 移动文件
mv extract_invocation_flow.py scripts/extract/
mv extract_tx_case0.py scripts/extract/
mv extract_all_cases.py scripts/extract/
mv extract_simple.py scripts/extract/
mv extract_invocation.js scripts/extract/

mv process_case0.py scripts/process/
mv process_all_cases.py scripts/process/

mv parse_invocation_flow.py scripts/parse/

mv convert_to_test_case.py scripts/utils/
mv pdf_to_markdown_simple.py scripts/utils/
```

### 步骤2: 组织文档（3分钟）

```bash
# 创建docs目录
mkdir -p docs/{deployment,development,setup}

# 移动文档
mv README_DOCKER.md docs/deployment/
mv QUICKSTART_DOCKER.md docs/deployment/
mv DOCKER_SETUP_COMPLETE.md docs/deployment/

mv README_WEB.md docs/development/
mv tests/README.md docs/development/testing.md

mv GITHUB_SETUP.md docs/setup/
mv SET_PRIVATE_REPO.md docs/setup/
mv FILES_TO_COMMIT.md docs/setup/
mv ARCHITECTURE_RECOMMENDATIONS.md docs/development/
mv REFACTORING_PLAN.md docs/development/
```

### 步骤3: 组织配置（2分钟）

```bash
mkdir -p config
mv test_cases.yaml config/
# 创建配置示例
touch config/.env.example
```

### 步骤4: 更新引用（10分钟）

需要更新的文件：
- `README.md` - 更新文档链接
- `app.py` - 如果引用了脚本路径
- `Dockerfile` - 如果引用了文件路径
- 脚本文件 - 更新相对路径

### 步骤5: 测试验证（5分钟）

```bash
# 运行测试确保一切正常
pytest

# 测试Web应用
python app.py

# 测试Docker构建
docker build -t test .
```

## ⚠️ 注意事项

1. **保持向后兼容** - 确保现有功能不受影响
2. **更新文档** - 更新所有文档中的路径引用
3. **更新.gitignore** - 确保新目录结构被正确处理
4. **测试验证** - 每个步骤后都要测试

## 🔄 迁移后的文件映射

| 原路径 | 新路径 |
|--------|--------|
| `extract_*.py` | `scripts/extract/` |
| `process_*.py` | `scripts/process/` |
| `parse_*.py` | `scripts/parse/` |
| `README_*.md` | `docs/` |
| `test_cases.yaml` | `config/` |
| `app.py` | 保持不变（根目录） |
| `convert_to_test_case_v2.py` | 保持不变（根目录） |

## 📝 检查清单

- [ ] 创建新目录结构
- [ ] 移动脚本文件
- [ ] 移动文档文件
- [ ] 移动配置文件
- [ ] 更新README.md中的路径
- [ ] 更新脚本中的导入路径
- [ ] 更新Dockerfile（如需要）
- [ ] 运行测试验证
- [ ] 测试Web应用
- [ ] 测试Docker构建
- [ ] 提交更改

## 🎯 下一步

完成方案A后，可以考虑：
1. 将核心代码移到 `src/` 目录（方案B）
2. 创建配置管理模块
3. 添加环境变量管理
4. 优化测试结构

