# GitHub上传指南

## ✅ 已完成

- ✅ Git仓库已初始化
- ✅ 所有文件已添加到暂存区
- ✅ 初始提交已创建

## 📤 推送到GitHub

### 步骤1: 在GitHub创建仓库

1. 登录GitHub
2. 点击右上角 "+" → "New repository"
3. 填写仓库信息：
   - Repository name: `CallTraceSniffer` (或您喜欢的名称)
   - Description: `BlockSec交易分析工具 - Web应用和Docker支持`
   - 选择 Public 或 Private
   - **不要**勾选 "Initialize this repository with a README"
4. 点击 "Create repository"

### 步骤2: 添加远程仓库并推送

```bash
# 方式1: 使用HTTPS（推荐，需要Personal Access Token）
git remote add origin https://github.com/YOUR_USERNAME/CallTraceSniffer.git
git branch -M main
git push -u origin main

# 方式2: 使用SSH（需要配置SSH key）
git remote add origin git@github.com:YOUR_USERNAME/CallTraceSniffer.git
git branch -M main
git push -u origin main
```

**注意**: 将 `YOUR_USERNAME` 替换为您的GitHub用户名

### 步骤3: 如果使用HTTPS，需要Personal Access Token

1. GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. 点击 "Generate new token (classic)"
3. 选择权限: `repo` (完整仓库访问)
4. 生成并复制token
5. 推送时使用token作为密码

## 🔄 后续更新

```bash
# 添加更改
git add .

# 提交更改
git commit -m "描述您的更改"

# 推送到GitHub
git push
```

## 📋 已提交的文件清单

### 核心应用
- `app.py` - Flask Web应用
- `src/calltrace/services/ir_v1_blocksec.py` - IR V1 解析模块
- `requirements.txt` - Python依赖

### Docker配置
- `Dockerfile` - Docker镜像配置
- `docker-compose.yml` - Docker Compose配置
- `.dockerignore` - Docker构建忽略文件
- `build_and_run.sh` - 一键构建运行脚本

### Web资源
- `templates/index.html` - 前端页面
- `static/css/style.css` - 样式文件
- `static/js/main.js` - JavaScript逻辑

### 文档
- `README.md` - 主文档
- `README_DOCKER.md` - Docker部署文档
- `README_WEB.md` - Web使用文档
- `QUICKSTART_DOCKER.md` - 快速开始指南
- `DOCKER_SETUP_COMPLETE.md` - Docker配置说明

### 示例文件
- `example_tx_hashes.csv` - CSV示例
- `test_cases.yaml` - 测试用例参考

### 配置文件
- `.gitignore` - Git忽略文件

## 🚫 未提交的文件（已忽略）

以下文件已在`.gitignore`中，不会上传：
- `venv/` - 虚拟环境
- `__pycache__/` - Python缓存
- `*.json`, `*.yaml`, `*.csv` - 数据文件（除了示例）
- `*.log` - 日志文件
- `.DS_Store` - macOS系统文件

## ✨ GitHub仓库设置建议

### 添加Topics（标签）
- `blockchain`
- `ethereum`
- `transaction-analysis`
- `flask`
- `docker`
- `playwright`
- `web-scraping`

### 添加描述
```
分析以太坊交易的Web应用，从BlockSec提取并生成 IR V1 JSON。支持Docker一键部署。
```

### 添加README徽章（可选）

在README.md顶部添加：

```markdown
![Docker](https://img.shields.io/badge/docker-ready-blue)
![Python](https://img.shields.io/badge/python-3.11+-blue)
![Flask](https://img.shields.io/badge/flask-3.0.0-green)
![License](https://img.shields.io/badge/license-MIT-green)
```

## 🔐 安全建议

1. **不要提交敏感信息**:
   - API密钥
   - 密码
   - 个人token

2. **使用环境变量**:
   - 创建`.env.example`文件作为模板
   - 将`.env`添加到`.gitignore`

3. **定期更新依赖**:
   ```bash
   pip list --outdated
   ```

## 📞 需要帮助？

如果推送遇到问题：

1. **认证失败**: 检查GitHub token或SSH key配置
2. **权限错误**: 确认仓库访问权限
3. **冲突**: 使用 `git pull` 先拉取远程更改
